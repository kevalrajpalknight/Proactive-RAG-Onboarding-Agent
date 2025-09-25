"""Metadata models for document filtering and retrieval."""

from typing import List, Optional, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class DocumentType(str, Enum):
    """Types of internal documents."""
    POLICY = "policy"
    PROCEDURE = "procedure"
    GUIDE = "guide"
    MANUAL = "manual"
    TRAINING = "training"
    FAQ = "faq"
    TEMPLATE = "template"
    FORM = "form"
    PRESENTATION = "presentation"
    VIDEO = "video"
    OTHER = "other"


class AccessLevel(str, Enum):
    """Document access levels."""
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"
    RESTRICTED = "restricted"


class DocumentMetadata(BaseModel):
    """Comprehensive metadata for internal documents."""
    
    # Basic document information
    document_id: str = Field(..., description="Unique document identifier")
    title: str = Field(..., description="Document title")
    document_type: DocumentType = Field(..., description="Type of document")
    
    # Content metadata
    description: Optional[str] = Field(None, description="Document description")
    topics: List[str] = Field(default_factory=list, description="Topics covered")
    keywords: List[str] = Field(default_factory=list, description="Keywords")
    
    # Organizational metadata
    department: Optional[str] = Field(None, description="Owning department")
    team: Optional[str] = Field(None, description="Owning team")
    author: Optional[str] = Field(None, description="Document author")
    
    # Role and audience metadata
    target_roles: List[str] = Field(
        default_factory=list, description="Roles this document targets"
    )
    seniority_levels: List[str] = Field(
        default_factory=list, description="Applicable seniority levels"
    )
    audience: List[str] = Field(
        default_factory=list, description="Target audience"
    )
    
    # Version and freshness
    version: Optional[str] = Field(None, description="Document version")
    created_date: Optional[datetime] = Field(None, description="Creation date")
    last_updated: Optional[datetime] = Field(None, description="Last update date")
    next_review_date: Optional[datetime] = Field(None, description="Next review date")
    
    # Access and security
    access_level: AccessLevel = Field(
        default=AccessLevel.INTERNAL, description="Access level"
    )
    required_clearance: Optional[str] = Field(None, description="Required clearance level")
    
    # Content characteristics
    language: str = Field(default="en", description="Document language")
    page_count: Optional[int] = Field(None, description="Number of pages")
    word_count: Optional[int] = Field(None, description="Word count")
    reading_time_minutes: Optional[int] = Field(None, description="Estimated reading time")
    
    # Relevance scoring
    importance_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Document importance score"
    )
    popularity_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Document popularity/usage score"
    )
    
    # Additional metadata
    tags: List[str] = Field(default_factory=list, description="Additional tags")
    custom_metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Custom metadata fields"
    )

    def is_relevant_for_role(self, role: str, department: Optional[str] = None) -> bool:
        """Check if document is relevant for a specific role."""
        if not self.target_roles:
            return True  # No specific targeting means generally relevant
            
        # Check direct role match
        if role.lower() in [r.lower() for r in self.target_roles]:
            return True
            
        # Check department relevance if provided
        if department and self.department:
            if department.lower() == self.department.lower():
                return True
                
        return False
    
    def is_fresh(self, max_age_days: int = 365) -> bool:
        """Check if document is considered fresh based on last update."""
        if not self.last_updated:
            return False
            
        age_days = (datetime.now() - self.last_updated).days
        return age_days <= max_age_days


class FilterCriteria(BaseModel):
    """Criteria for filtering documents during retrieval."""
    
    # Role-based filtering
    target_role: Optional[str] = Field(None, description="Target role")
    department: Optional[str] = Field(None, description="Department filter")
    seniority_level: Optional[str] = Field(None, description="Seniority level")
    
    # Document type filtering
    document_types: List[DocumentType] = Field(
        default_factory=list, description="Allowed document types"
    )
    exclude_types: List[DocumentType] = Field(
        default_factory=list, description="Document types to exclude"
    )
    
    # Content filtering
    required_topics: List[str] = Field(
        default_factory=list, description="Required topics"
    )
    preferred_topics: List[str] = Field(
        default_factory=list, description="Preferred topics (boost relevance)"
    )
    keywords: List[str] = Field(
        default_factory=list, description="Required keywords"
    )
    
    # Freshness filtering
    max_age_days: Optional[int] = Field(None, description="Maximum age in days")
    require_recent_update: bool = Field(
        default=False, description="Require recent updates"
    )
    
    # Quality filtering
    min_importance_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum importance score"
    )
    min_popularity_score: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Minimum popularity score"
    )
    
    # Access filtering
    max_access_level: AccessLevel = Field(
        default=AccessLevel.INTERNAL, description="Maximum access level allowed"
    )
    
    # Custom filtering
    custom_filters: Dict[str, Union[str, List[str], int, float, bool]] = Field(
        default_factory=dict, description="Custom filter criteria"
    )
    
    def matches_document(self, metadata: DocumentMetadata) -> bool:
        """Check if a document matches these filter criteria."""
        
        # Role-based filtering
        if self.target_role and not metadata.is_relevant_for_role(
            self.target_role, self.department
        ):
            return False
            
        # Document type filtering
        if self.document_types and metadata.document_type not in self.document_types:
            return False
            
        if metadata.document_type in self.exclude_types:
            return False
            
        # Topic filtering
        if self.required_topics:
            doc_topics = [t.lower() for t in metadata.topics]
            required_lower = [t.lower() for t in self.required_topics]
            if not any(topic in doc_topics for topic in required_lower):
                return False
                
        # Freshness filtering
        if self.max_age_days and not metadata.is_fresh(self.max_age_days):
            return False
            
        # Quality filtering
        if metadata.importance_score < self.min_importance_score:
            return False
            
        if metadata.popularity_score < self.min_popularity_score:
            return False
            
        # Access level filtering
        access_levels = {
            AccessLevel.PUBLIC: 0,
            AccessLevel.INTERNAL: 1,
            AccessLevel.CONFIDENTIAL: 2,
            AccessLevel.RESTRICTED: 3,
        }
        
        if access_levels[metadata.access_level] > access_levels[self.max_access_level]:
            return False
            
        return True
    
    def calculate_relevance_boost(self, metadata: DocumentMetadata) -> float:
        """Calculate relevance boost based on preferred criteria."""
        boost = 0.0
        
        # Boost for preferred topics
        if self.preferred_topics:
            doc_topics = [t.lower() for t in metadata.topics]
            preferred_lower = [t.lower() for t in self.preferred_topics]
            topic_matches = sum(1 for topic in preferred_lower if topic in doc_topics)
            boost += (topic_matches / len(self.preferred_topics)) * 0.2
            
        # Boost for exact role match
        if self.target_role and self.target_role.lower() in [
            r.lower() for r in metadata.target_roles
        ]:
            boost += 0.1
            
        # Boost for department match
        if self.department and metadata.department:
            if self.department.lower() == metadata.department.lower():
                boost += 0.1
                
        return min(boost, 0.5)  # Cap boost at 0.5