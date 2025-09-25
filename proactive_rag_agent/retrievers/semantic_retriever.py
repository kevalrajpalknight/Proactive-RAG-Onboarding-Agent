"""Semantic retriever using vector embeddings."""

import asyncio
from typing import List, Dict, Any, Optional
import numpy as np
from sentence_transformers import SentenceTransformer
import faiss
import json

from .base_retriever import BaseRetriever, RetrievalResult
from ..models.metadata import FilterCriteria, DocumentMetadata
from ..models.source import SourceCitation


class SemanticRetriever(BaseRetriever):
    """Semantic retriever using sentence transformers and FAISS."""
    
    def __init__(
        self,
        model_name: str = "all-MiniLM-L6-v2",
        index_type: str = "flat",
        dimension: Optional[int] = None
    ):
        """
        Initialize semantic retriever.
        
        Args:
            model_name: SentenceTransformer model to use
            index_type: FAISS index type ('flat', 'ivf', 'hnsw')
            dimension: Embedding dimension (auto-detected if None)
        """
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)
        self.dimension = dimension or self.model.get_sentence_embedding_dimension()
        
        # Initialize FAISS index
        if index_type == "flat":
            self.index = faiss.IndexFlatIP(self.dimension)  # Inner product for cosine similarity
        elif index_type == "ivf":
            quantizer = faiss.IndexFlatIP(self.dimension)
            self.index = faiss.IndexIVFFlat(quantizer, self.dimension, 100)  # 100 clusters
        elif index_type == "hnsw":
            self.index = faiss.IndexHNSWFlat(self.dimension, 32)  # M=32
        else:
            raise ValueError(f"Unsupported index type: {index_type}")
            
        # Storage for document metadata
        self.documents: Dict[int, Dict[str, Any]] = {}
        self.id_to_index: Dict[str, int] = {}
        self.next_index = 0
        
    async def retrieve(
        self,
        query: str,
        filters: Optional[FilterCriteria] = None,
        top_k: int = 10,
        similarity_threshold: float = 0.0,
        **kwargs
    ) -> List[RetrievalResult]:
        """Retrieve semantically similar documents."""
        
        # Encode query
        query_embedding = await self._encode_text(query)
        query_embedding = np.array([query_embedding]).astype('float32')
        
        # Normalize for cosine similarity
        faiss.normalize_L2(query_embedding)
        
        # Search in FAISS index
        search_k = min(top_k * 3, len(self.documents))  # Search more to allow for filtering
        if search_k == 0:
            return []
            
        scores, indices = self.index.search(query_embedding, search_k)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx == -1:  # FAISS returns -1 for empty slots
                continue
                
            if score < similarity_threshold:
                continue
                
            doc_data = self.documents[idx]
            metadata = DocumentMetadata(**doc_data['metadata'])
            
            # Apply filters if provided
            if filters and not filters.matches_document(metadata):
                continue
                
            # Create source citation
            source = SourceCitation(
                source_id=doc_data['id'],
                title=doc_data['title'],
                document_type=metadata.document_type,
                url=doc_data.get('url'),
                file_path=doc_data.get('file_path'),
                department=metadata.department,
                role_relevance=metadata.target_roles,
                topics=metadata.topics,
                last_updated=metadata.last_updated,
                relevance_score=float(score),
                confidence_score=metadata.importance_score,
                metadata=doc_data.get('extra_metadata', {})
            )
            
            # Apply relevance boost if filters provided
            relevance_boost = 0.0
            if filters:
                relevance_boost = filters.calculate_relevance_boost(metadata)
            
            result = RetrievalResult(
                content=doc_data['content'],
                source=source,
                relevance_score=float(score) + relevance_boost,
                metadata={
                    'original_score': float(score),
                    'relevance_boost': relevance_boost,
                    'retriever_type': 'semantic'
                }
            )
            
            results.append(result)
            
        # Sort by relevance score and return top_k
        results.sort(key=lambda x: x.relevance_score, reverse=True)
        return results[:top_k]
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        batch_size: int = 32,
        **kwargs
    ) -> None:
        """Add documents to the semantic index."""
        
        if not documents:
            return
            
        # Extract texts for embedding
        texts = []
        doc_data = []
        
        for doc in documents:
            # Combine title and content for embedding
            text = f"{doc['title']}\n{doc['content']}"
            texts.append(text)
            doc_data.append(doc)
            
        # Generate embeddings in batches
        embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = await self._encode_batch(batch_texts)
            embeddings.extend(batch_embeddings)
            
        # Convert to numpy array and normalize
        embeddings_array = np.array(embeddings).astype('float32')
        faiss.normalize_L2(embeddings_array)
        
        # Add to FAISS index
        start_idx = self.next_index
        self.index.add(embeddings_array)
        
        # Store document metadata
        for i, doc in enumerate(doc_data):
            idx = start_idx + i
            self.documents[idx] = doc
            self.id_to_index[doc['id']] = idx
            
        self.next_index += len(documents)
        
        # Train index if needed (for IVF)
        if hasattr(self.index, 'is_trained') and not self.index.is_trained:
            if len(self.documents) >= 100:  # Need enough data for training
                self.index.train(embeddings_array)
    
    async def update_document(
        self,
        document_id: str,
        document: Dict[str, Any],
        **kwargs
    ) -> None:
        """Update a document in the index."""
        
        if document_id not in self.id_to_index:
            raise ValueError(f"Document {document_id} not found in index")
            
        idx = self.id_to_index[document_id]
        
        # Generate new embedding
        text = f"{document['title']}\n{document['content']}"
        embedding = await self._encode_text(text)
        embedding_array = np.array([embedding]).astype('float32')
        faiss.normalize_L2(embedding_array)
        
        # Update in FAISS (requires rebuilding for most index types)
        # For now, we'll store the updated document and mark for rebuild
        self.documents[idx] = document
        
        # TODO: Implement incremental update or rebuild strategy
        
    async def delete_document(
        self,
        document_id: str,
        **kwargs
    ) -> None:
        """Delete a document from the index."""
        
        if document_id not in self.id_to_index:
            raise ValueError(f"Document {document_id} not found in index")
            
        idx = self.id_to_index[document_id]
        
        # Remove from storage
        del self.documents[idx]
        del self.id_to_index[document_id]
        
        # TODO: Implement removal from FAISS index (requires rebuild for most types)
    
    async def _encode_text(self, text: str) -> np.ndarray:
        """Encode a single text into embedding."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.model.encode, text)
    
    async def _encode_batch(self, texts: List[str]) -> List[np.ndarray]:
        """Encode a batch of texts into embeddings."""
        loop = asyncio.get_event_loop()
        embeddings = await loop.run_in_executor(None, self.model.encode, texts)
        return embeddings.tolist()
    
    def save_index(self, filepath: str) -> None:
        """Save the FAISS index and metadata to disk."""
        faiss.write_index(self.index, f"{filepath}.faiss")
        
        with open(f"{filepath}.metadata.json", 'w') as f:
            json.dump({
                'documents': self.documents,
                'id_to_index': self.id_to_index,
                'next_index': self.next_index,
                'model_name': self.model_name,
                'dimension': self.dimension
            }, f, default=str)
    
    def load_index(self, filepath: str) -> None:
        """Load the FAISS index and metadata from disk."""
        self.index = faiss.read_index(f"{filepath}.faiss")
        
        with open(f"{filepath}.metadata.json", 'r') as f:
            data = json.load(f)
            self.documents = {int(k): v for k, v in data['documents'].items()}
            self.id_to_index = data['id_to_index']
            self.next_index = data['next_index']
            
        # Reload model if different
        if data['model_name'] != self.model_name:
            self.model_name = data['model_name']
            self.model = SentenceTransformer(self.model_name)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the semantic index."""
        return {
            'total_documents': len(self.documents),
            'index_size': self.index.ntotal,
            'dimension': self.dimension,
            'model_name': self.model_name,
            'index_type': type(self.index).__name__
        }