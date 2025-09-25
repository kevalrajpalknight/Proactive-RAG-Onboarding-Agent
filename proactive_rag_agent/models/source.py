"""Source citation and content models."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field, HttpUrl


class SourceCitation(BaseModel):
    """Citation information for a source document."""
    
    source_id: str = Field(..., description="Unique identifier for the source")
    title: str = Field(..., description="Document title")
    document_type: str = Field(..., description="Type of document (e.g., policy, guide, manual)")
    url: Optional[HttpUrl] = Field(None, description="URL if available")
    file_path: Optional[str] = Field(None, description="File path if local document")
    
    # Metadata for filtering and relevance
    department: Optional[str] = Field(None, description="Associated department")
    role_relevance: List[str] = Field(
        default_factory=list, description="Roles this document is relevant for"
    )
    topics: List[str] = Field(
        default_factory=list, description="Topics covered in the document"
    )
    
    # Content metadata
    page_number: Optional[int] = Field(None, description="Specific page referenced")
    section: Optional[str] = Field(None, description="Specific section referenced")
    excerpt: Optional[str] = Field(None, description="Relevant excerpt from the source")
    
    # Quality and freshness
    last_updated: Optional[datetime] = Field(None, description="When document was last updated")
    relevance_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Relevance score for this citation"
    )
    confidence_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Confidence in the information"
    )
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    def to_citation_string(self) -> str:
        """Generate a formatted citation string."""
        citation_parts = [self.title]
        
        if self.section:
            citation_parts.append(f"Section: {self.section}")
        
        if self.page_number:
            citation_parts.append(f"Page: {self.page_number}")
            
        if self.url:
            citation_parts.append(f"URL: {self.url}")
        elif self.file_path:
            citation_parts.append(f"File: {self.file_path}")
            
        if self.last_updated:
            citation_parts.append(f"Updated: {self.last_updated.strftime('%Y-%m-%d')}")
            
        return " | ".join(citation_parts)


class CitedContent(BaseModel):
    """Content with associated source citations."""
    
    content: str = Field(..., description="The actual content")
    sources: List[SourceCitation] = Field(
        default_factory=list, description="Sources that contributed to this content"
    )
    generated_at: datetime = Field(
        default_factory=datetime.now, description="When this content was generated"
    )
    
    # Quality metrics
    source_coverage: float = Field(
        0.0, ge=0.0, le=1.0, description="How well sources cover the content"
    )
    hallucination_risk: float = Field(
        0.0, ge=0.0, le=1.0, description="Estimated risk of hallucinated content"
    )
    
    def get_citation_summary(self) -> str:
        """Get a summary of all citations."""
        if not self.sources:
            return "No sources cited"
            
        citation_strings = [source.to_citation_string() for source in self.sources]
        return "\n".join(f"[{i+1}] {citation}" for i, citation in enumerate(citation_strings))
    
    def get_unique_documents(self) -> List[str]:
        """Get list of unique document titles cited."""
        return list(set(source.title for source in self.sources))
    
    def calculate_average_confidence(self) -> float:
        """Calculate average confidence across all sources."""
        if not self.sources:
            return 0.0
        return sum(source.confidence_score for source in self.sources) / len(self.sources)