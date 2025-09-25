"""Metadata-based retriever for structured filtering."""

from typing import List, Dict, Any, Optional, Set
import re
from collections import defaultdict

from .base_retriever import BaseRetriever, RetrievalResult
from ..models.metadata import FilterCriteria, DocumentMetadata
from ..models.source import SourceCitation


class MetadataRetriever(BaseRetriever):
    """Retriever that uses structured metadata for precise filtering and ranking."""
    
    def __init__(self):
        """Initialize metadata retriever."""
        self.documents: Dict[str, Dict[str, Any]] = {}
        
        # Inverted indices for fast lookup
        self.topic_index: Dict[str, Set[str]] = defaultdict(set)
        self.keyword_index: Dict[str, Set[str]] = defaultdict(set)
        self.role_index: Dict[str, Set[str]] = defaultdict(set)
        self.department_index: Dict[str, Set[str]] = defaultdict(set)
        self.type_index: Dict[str, Set[str]] = defaultdict(set)
        
    async def retrieve(
        self,
        query: str,
        filters: Optional[FilterCriteria] = None,
        top_k: int = 10,
        use_query_expansion: bool = True,
        **kwargs
    ) -> List[RetrievalResult]:
        """Retrieve documents based on metadata matching and query analysis."""
        
        # Extract query terms and expand if needed
        query_terms = self._extract_query_terms(query.lower())
        if use_query_expansion:
            query_terms = self._expand_query_terms(query_terms)
        
        # Find candidate documents
        candidates = set(self.documents.keys())
        
        # Apply filters first
        if filters:
            candidates = self._apply_filters(candidates, filters)
        
        if not candidates:
            return []
        
        # Score documents based on query relevance and metadata
        scored_docs = []
        for doc_id in candidates:
            doc_data = self.documents[doc_id]
            metadata = DocumentMetadata(**doc_data['metadata'])
            
            # Calculate different relevance scores
            text_score = self._calculate_text_score(query_terms, doc_data)
            metadata_score = self._calculate_metadata_score(query_terms, metadata)
            quality_score = self._calculate_quality_score(metadata)
            
            # Combine scores with weights
            total_score = (
                0.4 * text_score +
                0.4 * metadata_score +
                0.2 * quality_score
            )
            
            # Apply filter boosts
            if filters:
                boost = filters.calculate_relevance_boost(metadata)
                total_score += boost
            
            # Create source citation
            source = SourceCitation(
                source_id=doc_id,
                title=doc_data['title'],
                document_type=metadata.document_type,
                url=doc_data.get('url'),
                file_path=doc_data.get('file_path'),
                department=metadata.department,
                role_relevance=metadata.target_roles,
                topics=metadata.topics,
                last_updated=metadata.last_updated,
                relevance_score=total_score,
                confidence_score=metadata.importance_score,
                metadata=doc_data.get('extra_metadata', {})
            )
            
            result = RetrievalResult(
                content=doc_data['content'],
                source=source,
                relevance_score=total_score,
                metadata={
                    'text_score': text_score,
                    'metadata_score': metadata_score,
                    'quality_score': quality_score,
                    'retriever_type': 'metadata'
                }
            )
            
            scored_docs.append(result)
        
        # Sort by score and return top_k
        scored_docs.sort(key=lambda x: x.relevance_score, reverse=True)
        return scored_docs[:top_k]
    
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        **kwargs
    ) -> None:
        """Add documents to the metadata index."""
        
        for doc in documents:
            doc_id = doc['id']
            self.documents[doc_id] = doc
            
            # Update inverted indices
            self._update_indices(doc_id, doc)
    
    async def update_document(
        self,
        document_id: str,
        document: Dict[str, Any],
        **kwargs
    ) -> None:
        """Update a document in the metadata index."""
        
        if document_id not in self.documents:
            raise ValueError(f"Document {document_id} not found in index")
        
        # Remove old indices
        self._remove_from_indices(document_id)
        
        # Update document and rebuild indices
        self.documents[document_id] = document
        self._update_indices(document_id, document)
    
    async def delete_document(
        self,
        document_id: str,
        **kwargs
    ) -> None:
        """Delete a document from the metadata index."""
        
        if document_id not in self.documents:
            raise ValueError(f"Document {document_id} not found in index")
        
        # Remove from indices and storage
        self._remove_from_indices(document_id)
        del self.documents[document_id]
    
    def _extract_query_terms(self, query: str) -> List[str]:
        """Extract meaningful terms from the query."""
        # Simple tokenization - could be enhanced with NLP
        terms = re.findall(r'\b\w+\b', query.lower())
        
        # Filter out common stop words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'over', 'under', 'again', 'further',
            'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all',
            'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            'can', 'will', 'just', 'should', 'now'
        }
        
        return [term for term in terms if term not in stop_words and len(term) > 2]
    
    def _expand_query_terms(self, terms: List[str]) -> List[str]:
        """Expand query terms with synonyms and related terms."""
        # Simple expansion - could be enhanced with thesaurus or word embeddings
        expansions = {
            'training': ['learning', 'education', 'development', 'course'],
            'policy': ['procedure', 'guideline', 'rule', 'standard'],
            'manager': ['supervisor', 'lead', 'director', 'boss'],
            'team': ['group', 'department', 'unit', 'squad'],
            'process': ['procedure', 'workflow', 'method', 'approach'],
            'software': ['application', 'system', 'tool', 'platform'],
            'onboarding': ['orientation', 'introduction', 'induction', 'welcome'],
        }
        
        expanded = list(terms)
        for term in terms:
            if term in expansions:
                expanded.extend(expansions[term])
        
        return list(set(expanded))  # Remove duplicates
    
    def _apply_filters(
        self, 
        candidates: Set[str], 
        filters: FilterCriteria
    ) -> Set[str]:
        """Apply filter criteria to candidate documents."""
        
        filtered = set(candidates)
        
        # Filter by document type
        if filters.document_types:
            type_matches = set()
            for doc_type in filters.document_types:
                type_matches.update(self.type_index[doc_type.value])
            filtered &= type_matches
        
        # Exclude document types
        if filters.exclude_types:
            for doc_type in filters.exclude_types:
                filtered -= self.type_index[doc_type.value]
        
        # Filter by role
        if filters.target_role:
            role_matches = self.role_index[filters.target_role.lower()]
            filtered &= role_matches
        
        # Filter by department
        if filters.department:
            dept_matches = self.department_index[filters.department.lower()]
            filtered &= dept_matches
        
        # Filter by required topics
        if filters.required_topics:
            for topic in filters.required_topics:
                topic_matches = self.topic_index[topic.lower()]
                filtered &= topic_matches
        
        # Filter by keywords
        if filters.keywords:
            for keyword in filters.keywords:
                keyword_matches = self.keyword_index[keyword.lower()]
                filtered &= keyword_matches
        
        # Apply document-level filters
        final_filtered = set()
        for doc_id in filtered:
            doc_data = self.documents[doc_id]
            metadata = DocumentMetadata(**doc_data['metadata'])
            
            if filters.matches_document(metadata):
                final_filtered.add(doc_id)
        
        return final_filtered
    
    def _calculate_text_score(
        self, 
        query_terms: List[str], 
        doc_data: Dict[str, Any]
    ) -> float:
        """Calculate text relevance score."""
        
        # Combine title and content for scoring
        text = f"{doc_data['title']} {doc_data['content']}".lower()
        
        # Count term matches
        matches = 0
        total_terms = len(query_terms)
        
        if total_terms == 0:
            return 0.0
        
        for term in query_terms:
            if term in text:
                matches += 1
        
        # Basic TF score with title boost
        title_text = doc_data['title'].lower()
        title_matches = sum(1 for term in query_terms if term in title_text)
        
        score = (matches / total_terms) + (title_matches / total_terms) * 0.5
        return min(score, 1.0)
    
    def _calculate_metadata_score(
        self, 
        query_terms: List[str], 
        metadata: DocumentMetadata
    ) -> float:
        """Calculate metadata relevance score."""
        
        if not query_terms:
            return 0.0
        
        score = 0.0
        
        # Check topics
        topics_text = ' '.join(metadata.topics).lower()
        topic_matches = sum(1 for term in query_terms if term in topics_text)
        score += (topic_matches / len(query_terms)) * 0.4
        
        # Check keywords
        keywords_text = ' '.join(metadata.keywords).lower()
        keyword_matches = sum(1 for term in query_terms if term in keywords_text)
        score += (keyword_matches / len(query_terms)) * 0.3
        
        # Check description
        if metadata.description:
            desc_text = metadata.description.lower()
            desc_matches = sum(1 for term in query_terms if term in desc_text)
            score += (desc_matches / len(query_terms)) * 0.2
        
        # Check tags
        tags_text = ' '.join(metadata.tags).lower()
        tag_matches = sum(1 for term in query_terms if term in tags_text)
        score += (tag_matches / len(query_terms)) * 0.1
        
        return min(score, 1.0)
    
    def _calculate_quality_score(self, metadata: DocumentMetadata) -> float:
        """Calculate document quality score."""
        
        # Combine importance and popularity scores
        quality = (metadata.importance_score + metadata.popularity_score) / 2
        
        # Boost for recent updates
        if metadata.is_fresh(max_age_days=90):
            quality += 0.1
        elif metadata.is_fresh(max_age_days=365):
            quality += 0.05
        
        return min(quality, 1.0)
    
    def _update_indices(self, doc_id: str, doc_data: Dict[str, Any]) -> None:
        """Update inverted indices for a document."""
        
        metadata = DocumentMetadata(**doc_data['metadata'])
        
        # Index topics
        for topic in metadata.topics:
            self.topic_index[topic.lower()].add(doc_id)
        
        # Index keywords
        for keyword in metadata.keywords:
            self.keyword_index[keyword.lower()].add(doc_id)
        
        # Index roles
        for role in metadata.target_roles:
            self.role_index[role.lower()].add(doc_id)
        
        # Index department
        if metadata.department:
            self.department_index[metadata.department.lower()].add(doc_id)
        
        # Index document type
        self.type_index[metadata.document_type.value].add(doc_id)
        
        # Index tags
        for tag in metadata.tags:
            self.keyword_index[tag.lower()].add(doc_id)
    
    def _remove_from_indices(self, doc_id: str) -> None:
        """Remove document from all inverted indices."""
        
        # Remove from all indices
        for index in [
            self.topic_index, self.keyword_index, self.role_index,
            self.department_index, self.type_index
        ]:
            for term_set in index.values():
                term_set.discard(doc_id)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get statistics about the metadata index."""
        
        return {
            'total_documents': len(self.documents),
            'unique_topics': len(self.topic_index),
            'unique_keywords': len(self.keyword_index),  
            'unique_roles': len(self.role_index),
            'unique_departments': len(self.department_index),
            'document_types': len(self.type_index)
        }