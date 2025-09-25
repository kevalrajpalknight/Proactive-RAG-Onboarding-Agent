"""Base retriever interface."""

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
from pydantic import BaseModel

from ..models.metadata import FilterCriteria
from ..models.source import SourceCitation


class RetrievalResult(BaseModel):
    """Result from a retriever query."""
    
    content: str
    source: SourceCitation
    relevance_score: float
    metadata: Dict[str, Any] = {}


class BaseRetriever(ABC):
    """Abstract base class for all retrievers."""
    
    @abstractmethod
    async def retrieve(
        self,
        query: str,
        filters: Optional[FilterCriteria] = None,
        top_k: int = 10,
        **kwargs
    ) -> List[RetrievalResult]:
        """
        Retrieve relevant documents based on query and filters.
        
        Args:
            query: The search query
            filters: Optional filtering criteria
            top_k: Maximum number of results to return
            **kwargs: Additional retriever-specific parameters
            
        Returns:
            List of retrieval results sorted by relevance
        """
        pass
    
    @abstractmethod
    async def add_documents(
        self,
        documents: List[Dict[str, Any]],
        **kwargs
    ) -> None:
        """
        Add documents to the retriever's index.
        
        Args:
            documents: List of documents to add
            **kwargs: Additional parameters for indexing
        """
        pass
    
    @abstractmethod
    async def update_document(
        self,
        document_id: str,
        document: Dict[str, Any],
        **kwargs
    ) -> None:
        """
        Update a specific document in the index.
        
        Args:
            document_id: ID of document to update
            document: Updated document data
            **kwargs: Additional parameters
        """
        pass
    
    @abstractmethod
    async def delete_document(
        self,
        document_id: str,
        **kwargs
    ) -> None:
        """
        Delete a document from the index.
        
        Args:
            document_id: ID of document to delete
            **kwargs: Additional parameters
        """
        pass
    
    def get_retriever_type(self) -> str:
        """Get the type of this retriever."""
        return self.__class__.__name__