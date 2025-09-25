"""Configuration settings for the agent."""

from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field, validator
from pathlib import Path
import os


class LLMConfig(BaseModel):
    """Configuration for the Language Model."""
    
    provider: str = Field(default="openai", description="LLM provider")
    model_name: str = Field(default="gpt-3.5-turbo", description="Model name")
    temperature: float = Field(default=0.1, ge=0.0, le=2.0, description="Generation temperature")
    max_tokens: int = Field(default=2000, ge=1, description="Maximum tokens per response")
    
    # API configuration
    api_key: Optional[str] = Field(None, description="API key for the provider")
    api_base: Optional[str] = Field(None, description="Custom API base URL")
    
    # Generation parameters
    top_p: float = Field(default=0.9, ge=0.0, le=1.0, description="Top-p sampling")
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Frequency penalty")
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0, description="Presence penalty")
    
    # Rate limiting
    requests_per_minute: int = Field(default=50, ge=1, description="Max requests per minute")
    max_retries: int = Field(default=3, ge=0, description="Max retry attempts")


class RetrieverConfig(BaseModel):
    """Configuration for the dual retriever."""
    
    # Semantic retriever settings
    semantic_model: str = Field(
        default="all-MiniLM-L6-v2", 
        description="Sentence transformer model"
    )
    semantic_index_type: str = Field(
        default="flat", 
        description="FAISS index type (flat, ivf, hnsw)"
    )
    
    # Fusion settings
    semantic_weight: float = Field(
        default=0.6, ge=0.0, le=1.0, description="Weight for semantic retrieval"
    )
    metadata_weight: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Weight for metadata retrieval"
    )
    fusion_method: str = Field(
        default="weighted_sum", 
        description="Score fusion method (weighted_sum, rrf, max)"
    )
    
    # Retrieval parameters
    default_top_k: int = Field(default=10, ge=1, description="Default number of results")
    semantic_top_k_multiplier: float = Field(
        default=2.0, ge=1.0, description="Multiplier for semantic retrieval count"
    )
    metadata_top_k_multiplier: float = Field(
        default=2.0, ge=1.0, description="Multiplier for metadata retrieval count"
    )
    
    # Quality thresholds
    min_similarity_threshold: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Minimum similarity threshold"
    )
    min_sources_per_task: int = Field(
        default=1, ge=1, description="Minimum sources per curriculum task"
    )
    
    @validator('semantic_weight', 'metadata_weight')
    def validate_weights_sum(cls, v, values):
        """Validate that weights sum to 1.0."""
        if 'semantic_weight' in values:
            if abs(values['semantic_weight'] + v - 1.0) > 0.001:
                raise ValueError("Semantic and metadata weights must sum to 1.0")
        return v


class CurriculumConfig(BaseModel):
    """Configuration for curriculum generation."""
    
    # Structure requirements
    weeks_count: int = Field(default=4, ge=1, le=8, description="Number of weeks")
    days_per_week: int = Field(default=5, ge=1, le=7, description="Working days per week")
    
    # Time allocation
    max_hours_per_day: float = Field(
        default=8.0, ge=1.0, le=16.0, description="Maximum hours per day"
    )
    min_hours_per_day: float = Field(
        default=4.0, ge=1.0, le=8.0, description="Minimum hours per day"
    )
    
    # Task distribution
    reading_task_percentage: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Percentage of reading tasks"
    )
    hands_on_percentage: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Percentage of hands-on tasks"
    )
    meeting_percentage: float = Field(
        default=0.2, ge=0.0, le=1.0, description="Percentage of meeting tasks"
    )
    assessment_percentage: float = Field(
        default=0.1, ge=0.0, le=1.0, description="Percentage of assessment tasks"
    )
    
    # Quality requirements
    min_sources_per_week: int = Field(
        default=5, ge=1, description="Minimum sources per week"
    )
    max_tasks_per_day: int = Field(
        default=6, ge=1, description="Maximum tasks per day"
    )
    require_weekly_assessments: bool = Field(
        default=True, description="Require assessments each week"
    )
    
    # Customization factors
    role_specific_weight: float = Field(
        default=0.4, ge=0.0, le=1.0, description="Weight for role-specific content"
    )
    department_specific_weight: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Weight for department-specific content"
    )
    general_knowledge_weight: float = Field(
        default=0.3, ge=0.0, le=1.0, description="Weight for general knowledge"
    )


class AgentConfig(BaseModel):
    """Main configuration for the Proactive RAG Agent."""
    
    # Component configurations
    llm: LLMConfig = Field(default_factory=LLMConfig)
    retriever: RetrieverConfig = Field(default_factory=RetrieverConfig)
    curriculum: CurriculumConfig = Field(default_factory=CurriculumConfig)
    
    # Data paths
    documents_path: str = Field(
        default="./data/documents", description="Path to document storage"
    )
    index_path: str = Field(
        default="./data/indices", description="Path to index storage"
    )
    cache_path: str = Field(
        default="./data/cache", description="Path to cache storage"
    )
    
    # Processing settings
    batch_size: int = Field(default=32, ge=1, description="Batch size for processing")
    max_concurrent_requests: int = Field(
        default=5, ge=1, description="Max concurrent API requests"
    )
    
    # Quality and validation
    enable_citation_validation: bool = Field(
        default=True, description="Enable source citation validation"
    )
    enable_hallucination_detection: bool = Field(
        default=True, description="Enable hallucination detection"
    )
    min_confidence_threshold: float = Field(
        default=0.7, ge=0.0, le=1.0, description="Minimum confidence for outputs"
    )
    
    # Logging and monitoring
    log_level: str = Field(default="INFO", description="Logging level")
    enable_metrics: bool = Field(default=True, description="Enable metrics collection")
    metrics_export_interval: int = Field(
        default=300, ge=60, description="Metrics export interval in seconds"
    )
    
    # Environment overrides from .env
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._load_from_env()
    
    def _load_from_env(self):
        """Load configuration from environment variables."""
        
        # LLM configuration
        if os.getenv("OPENAI_API_KEY"):
            self.llm.api_key = os.getenv("OPENAI_API_KEY")
        if os.getenv("LLM_MODEL"):
            self.llm.model_name = os.getenv("LLM_MODEL")
        if os.getenv("LLM_TEMPERATURE"):
            self.llm.temperature = float(os.getenv("LLM_TEMPERATURE"))
        
        # Path configuration
        if os.getenv("DOCUMENTS_PATH"):
            self.documents_path = os.getenv("DOCUMENTS_PATH")
        if os.getenv("INDEX_PATH"):
            self.index_path = os.getenv("INDEX_PATH")
        if os.getenv("CACHE_PATH"):
            self.cache_path = os.getenv("CACHE_PATH")
        
        # Retriever configuration
        if os.getenv("SEMANTIC_MODEL"):
            self.retriever.semantic_model = os.getenv("SEMANTIC_MODEL")
    
    def create_directories(self):
        """Create necessary directories if they don't exist.""" 
        
        directories = [
            self.documents_path,
            self.index_path,
            self.cache_path
        ]
        
        for directory in directories:
            Path(directory).mkdir(parents=True, exist_ok=True)
    
    def validate_config(self) -> Dict[str, List[str]]:
        """Validate configuration and return any issues."""
        
        issues = {
            'errors': [],
            'warnings': []
        }
        
        # Check API key
        if not self.llm.api_key:
            issues['errors'].append("LLM API key is required")
        
        # Check path accessibility
        for path_name, path_value in [
            ("documents_path", self.documents_path),
            ("index_path", self.index_path),  
            ("cache_path", self.cache_path)
        ]:
            try:
                Path(path_value).mkdir(parents=True, exist_ok=True)
            except PermissionError:
                issues['errors'].append(f"Cannot create directory: {path_value}")
        
        # Check percentage allocations sum
        total_percentage = (
            self.curriculum.reading_task_percentage +
            self.curriculum.hands_on_percentage +
            self.curriculum.meeting_percentage +
            self.curriculum.assessment_percentage
        )
        if abs(total_percentage - 1.0) > 0.01:
            issues['warnings'].append(
                f"Task percentages sum to {total_percentage:.2f}, not 1.0"
            )
        
        return issues