"""Dual retriever that combines semantic and metadata-based retrieval."""

from typing import List, Dict, Any, Optional
import asyncio
from collections import defaultdict

from .base_retriever import BaseRetriever, RetrievalResult
from .semantic_retriever import SemanticRetriever
from .metadata_retriever import MetadataRetriever
from ..models.metadata import FilterCriteria


class DualRetriever(BaseRetriever):
    """
    Dual retriever combining semantic and metadata-based retrieval.
    
    This retriever uses both semantic similarity and structured metadata
    to provide comprehensive and accurate document retrieval for onboarding.
    """
    
    def __init__(
        self,
        semantic_model: str = "all-MiniLM-L6-v2",
        semantic_weight: float = 0.6,
        metadata_weight: float = 0.4,
        fusion_method: str = "weighted_sum"
    ):
        """
        Initialize dual retriever.
        
        Args:
            semantic_model: Model name for semantic retriever
            semantic_weight: Weight for semantic retrieval scores
            metadata_weight: Weight for metadata retrieval scores  
            fusion_method: Method for combining scores ('weighted_sum', 'rrf', 'max')
        """
        self.semantic_retriever = SemanticRetriever(model_name=semantic_model)
        self.metadata_retriever = MetadataRetriever()
        
        self.semantic_weight = semantic_weight
        self.metadata_weight = metadata_weight
        self.fusion_method = fusion_method
        
        # Validate weights
        if abs(semantic_weight + metadata_weight - 1.0) > 0.001:
            raise ValueError("Semantic and metadata weights must sum to 1.0")
    
    async def retrieve(
        self,
        query: str,
        filters: Optional[FilterCriteria] = None,
        top_k: int = 10,
        semantic_top_k: Optional[int] = None,
        metadata_top_k: Optional[int] = None,
        min_sources: int = 2,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        Retrieve documents using both semantic and metadata approaches.
        
        Args:
            query: Search query
            filters: Optional filtering criteria
            top_k: Final number of results to return
            semantic_top_k: Number of results from semantic retriever (default: top_k * 2)
            metadata_top_k: Number of results from metadata retriever (default: top_k * 2)
            min_sources: Minimum number of sources per retriever (default: 2)
            **kwargs: Additional parameters
            
        Returns:
            Fused and ranked retrieval results
        """
        
        # Set default retrieval counts
        semantic_top_k = semantic_top_k or max(top_k * 2, min_sources)
        metadata_top_k = metadata_top_k or max(top_k * 2, min_sources)
        
        # Retrieve from both sources concurrently
        semantic_task = self.semantic_retriever.retrieve(
            query=query,
            filters=filters,
            top_k=semantic_top_k,
            **kwargs
        )
        
        metadata_task = self.metadata_retriever.retrieve(
            query=query,
            filters=filters,
            top_k=metadata_top_k,
            **kwargs
        )
        
        semantic_results, metadata_results = await asyncio.gather(
            semantic_task, metadata_task
        )
        
        # Fuse results
        fused_results = self._fuse_results(
            semantic_results, 
            metadata_results,
            query=query
        )
        
        # Apply final ranking and return top_k
        final_results = self._final_ranking(fused_results, top_k)
        
        return final_results
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Add documents to both retrievers."""
        
        # Add to both retrievers concurrently
        await asyncio.gather(
            self.semantic_retriever.add_documents(documents, **kwargs),
            self.metadata_retriever.add_documents(documents, **kwargs)
        )
    
    async def update_document(
        self,
        document_id: str,
        document: Dict[str, Any],
        **kwargs
    ) -> None:
        """Update document in both retrievers."""
        
        await asyncio.gather(
            self.semantic_retriever.update_document(document_id, document, **kwargs),
            self.metadata_retriever.update_document(document_id, document, **kwargs)
        )
    
    async def delete_document(
        self,
        document_id: str,
        **kwargs
    ) -> None:
        """Delete document from both retrievers."""
        
        await asyncio.gather(
            self.semantic_retriever.delete_document(document_id, **kwargs),
            self.metadata_retriever.delete_document(document_id, **kwargs)
        )
    
    def _fuse_results(
        self,
        semantic_results: List[RetrievalResult],
        metadata_results: List[RetrievalResult],
        query: str
    ) -> List[RetrievalResult]:
        """Fuse results from both retrievers."""
        
        # Group results by document ID
        doc_results: Dict[str, Dict[str, RetrievalResult]] = defaultdict(dict)
        
        # Add semantic results
        for result in semantic_results:
            doc_id = result.source.source_id
            doc_results[doc_id]['semantic'] = result
        
        # Add metadata results  
        for result in metadata_results:
            doc_id = result.source.source_id
            doc_results[doc_id]['metadata'] = result
        
        # Fuse scores for each document
        fused_results = []
        
        for doc_id, retriever_results in doc_results.items():
            semantic_result = retriever_results.get('semantic')
            metadata_result = retriever_results.get('metadata')
            
            if self.fusion_method == "weighted_sum":
                fused_score = self._weighted_sum_fusion(semantic_result, metadata_result)
            elif self.fusion_method == "rrf":
                fused_score = self._reciprocal_rank_fusion(
                    semantic_result, metadata_result, semantic_results, metadata_results
                )
            elif self.fusion_method == "max":
                fused_score = self._max_fusion(semantic_result, metadata_result)
            else:
                raise ValueError(f"Unknown fusion method: {self.fusion_method}")
            
            # Create fused result (prefer semantic result as base, fallback to metadata)
            base_result = semantic_result or metadata_result
            
            # Combine metadata from both sources
            combined_metadata = {}
            if semantic_result:
                combined_metadata.update(semantic_result.metadata)
            if metadata_result:
                combined_metadata.update(metadata_result.metadata)
            
            combined_metadata.update({
                'fusion_method': self.fusion_method,
                'semantic_score': semantic_result.relevance_score if semantic_result else 0.0,
                'metadata_score': metadata_result.relevance_score if metadata_result else 0.0,
                'fused_score': fused_score,
                'has_semantic': semantic_result is not None,
                'has_metadata': metadata_result is not None
            })
            
            fused_result = RetrievalResult(
                content=base_result.content,
                source=base_result.source,
                relevance_score=fused_score,
                metadata=combined_metadata
            )
            
            fused_results.append(fused_result)
        
        return fused_results
    
    def _weighted_sum_fusion(
        self,
        semantic_result: Optional[RetrievalResult],
        metadata_result: Optional[RetrievalResult]
    ) -> float:
        """Combine scores using weighted sum."""
        
        semantic_score = semantic_result.relevance_score if semantic_result else 0.0
        metadata_score = metadata_result.relevance_score if metadata_result else 0.0
        
        return (
            self.semantic_weight * semantic_score +
            self.metadata_weight * metadata_score
        )
    
    def _reciprocal_rank_fusion(
        self,
        semantic_result: Optional[RetrievalResult],
        metadata_result: Optional[RetrievalResult],
        semantic_results: List[RetrievalResult],
        metadata_results: List[RetrievalResult],
        k: int = 60
    ) -> float:
        """Combine using Reciprocal Rank Fusion (RRF)."""
        
        rrf_score = 0.0
        
        # Add semantic rank contribution
        if semantic_result:
            try:
                semantic_rank = semantic_results.index(semantic_result) + 1
                rrf_score += self.semantic_weight / (k + semantic_rank)
            except ValueError:
                pass
        
        # Add metadata rank contribution
        if metadata_result:
            try:
                metadata_rank = metadata_results.index(metadata_result) + 1
                rrf_score += self.metadata_weight / (k + metadata_rank)
            except ValueError:
                pass
        
        return rrf_score
    
    def _max_fusion(
        self,
        semantic_result: Optional[RetrievalResult],
        metadata_result: Optional[RetrievalResult]
    ) -> float:
        """Take maximum score from either retriever."""
        
        scores = []
        if semantic_result:
            scores.append(semantic_result.relevance_score)
        if metadata_result:
            scores.append(metadata_result.relevance_score)
        
        return max(scores) if scores else 0.0
    
    def _final_ranking(
        self,
        results: List[RetrievalResult],
        top_k: int
    ) -> List[RetrievalResult]:
        """Apply final ranking and diversity considerations."""
        
        # Sort by fused score
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        
        # Apply diversity filtering to avoid too many results from same source
        diverse_results = []
        source_counts = defaultdict(int)
        max_per_source = max(1, top_k // 3)  # Limit results per source
        
        for result in results:
            source_title = result.source.title
            
            if (source_counts[source_title] < max_per_source or 
                len(diverse_results) < top_k // 2):  # Always allow top half
                diverse_results.append(result)
                source_counts[source_title] += 1
                
                if len(diverse_results) >= top_k:
                    break
        
        return diverse_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get combined statistics from both retrievers."""
        
        semantic_stats = self.semantic_retriever.get_stats()
        metadata_stats = self.metadata_retriever.get_stats()
        
        return {
            'fusion_method': self.fusion_method,
            'semantic_weight': self.semantic_weight,
            'metadata_weight': self.metadata_weight,
            'semantic_retriever': semantic_stats,
            'metadata_retriever': metadata_stats
        }
    
    def save_indices(self, base_path: str) -> None:
        """Save both retriever indices."""
        self.semantic_retriever.save_index(f"{base_path}_semantic")
        # Metadata retriever doesn't need explicit saving (in-memory)
    
    def load_indices(self, base_path: str) -> None:
        """Load both retriever indices."""
        self.semantic_retriever.load_index(f"{base_path}_semantic")
        # Metadata retriever will be rebuilt when documents are added