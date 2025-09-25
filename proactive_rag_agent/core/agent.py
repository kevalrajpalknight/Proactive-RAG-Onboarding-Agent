"""Main Proactive RAG Onboarding Agent."""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

from ..config import AgentConfig, load_config
from ..retrievers import DualRetriever
from ..models import CurriculumPlan, FilterCriteria, DocumentMetadata
from .curriculum_generator import CurriculumGenerator
from .document_processor import DocumentProcessor


logger = logging.getLogger(__name__)


class OnboardingAgent:
    """
    Main Proactive RAG Onboarding Agent.
    
    This agent orchestrates the entire onboarding curriculum generation process,
    combining dual retrieval, LLM generation, and Pydantic validation to create
    tailored 30-day curricula with source citations.
    """
    
    def __init__(
        self,
        config: Optional[AgentConfig] = None,
        config_path: Optional[str] = None
    ):
        """
        Initialize the Onboarding Agent.
        
        Args:
            config: Agent configuration object
            config_path: Path to configuration file  
        """
        
        # Load configuration
        if config:
            self.config = config
        else:
            self.config = load_config(config_path)
        
        # Validate configuration
        config_issues = self.config.validate_config()
        if config_issues['errors']:
            raise ValueError(f"Configuration errors: {config_issues['errors']}")
        
        if config_issues['warnings']:
            logger.warning(f"Configuration warnings: {config_issues['warnings']}")
        
        # Create necessary directories
        self.config.create_directories()
        
        # Initialize components
        self.retriever = DualRetriever(
            semantic_model=self.config.retriever.semantic_model,
            semantic_weight=self.config.retriever.semantic_weight,
            metadata_weight=self.config.retriever.metadata_weight,
            fusion_method=self.config.retriever.fusion_method
        )
        
        self.curriculum_generator = CurriculumGenerator(
            config=self.config,
            retriever=self.retriever
        )
        
        self.document_processor = DocumentProcessor(config=self.config)
        
        # Track initialization status
        self._initialized = False
        self._documents_loaded = False
        
        logger.info("Proactive RAG Onboarding Agent initialized")
    
    async def initialize(self, force: bool = False) -> None:
        """
        Initialize the agent and load existing indices.
        
        Args:
            force: Force re-initialization even if already initialized
        """
        
        if self._initialized and not force:
            return
        
        logger.info("Initializing agent components...")
        
        # Try to load existing indices
        index_path = Path(self.config.index_path) / "dual_retriever"
        if index_path.exists():
            try:
                self.retriever.load_indices(str(index_path))
                self._documents_loaded = True
                logger.info("Loaded existing retriever indices")
            except Exception as e:
                logger.warning(f"Failed to load existing indices: {e}")
        
        # Initialize curriculum generator
        await self.curriculum_generator.initialize()
        
        self._initialized = True
        logger.info("Agent initialization complete")
    
    async def add_documents(
        self,
        document_paths: List[str],
        force_reindex: bool = False
    ) -> Dict[str, Any]:
        """
        Add documents to the agent's knowledge base.
        
        Args:
            document_paths: List of paths to documents or directories
            force_reindex: Force re-indexing even if documents exist
            
        Returns:
            Processing results and statistics
        """
        
        await self.initialize()
        
        logger.info(f"Processing {len(document_paths)} document paths...")
        
        # Process documents
        processed_docs = await self.document_processor.process_documents(
            document_paths,
            force_reprocess=force_reindex
        )
        
        if not processed_docs:
            logger.warning("No documents were processed")
            return {
                'processed_count': 0,
                'success': False,
                'message': "No documents to process"
            }
        
        # Add to retriever
        await self.retriever.add_documents(processed_docs)
        
        # Save indices
        index_path = Path(self.config.index_path) / "dual_retriever"
        index_path.parent.mkdir(parents=True, exist_ok=True)
        self.retriever.save_indices(str(index_path))
        
        self._documents_loaded = True
        
        stats = {
            'processed_count': len(processed_docs),
            'success': True,
            'retriever_stats': self.retriever.get_stats()
        }
        
        logger.info(f"Successfully processed {len(processed_docs)} documents")
        return stats
    
    async def generate_curriculum(
        self,
        role_title: str,
        department: str,
        seniority_level: str = "junior",
        employee_id: Optional[str] = None,
        custom_requirements: Optional[List[str]] = None,
        custom_filters: Optional[FilterCriteria] = None
    ) -> CurriculumPlan:
        """
        Generate a tailored 30-day onboarding curriculum.
        
        Args:
            role_title: Target role title
            department: Department  
            seniority_level: Seniority level (junior, mid, senior)
            employee_id: Optional employee identifier
            custom_requirements: Additional requirements to consider
            custom_filters: Custom filtering criteria
            
        Returns:
            Generated and validated curriculum plan
            
        Raises:
            ValueError: If agent not properly initialized
            RuntimeError: If curriculum generation fails
        """
        
        await self.initialize()
        
        if not self._documents_loaded:
            raise ValueError(
                "No documents loaded. Use add_documents() first to build knowledge base."
            )
        
        logger.info(
            f"Generating curriculum for {role_title} in {department} "
            f"(seniority: {seniority_level})"
        )
        
        try:
            # Generate curriculum
            curriculum = await self.curriculum_generator.generate_curriculum(
                role_title=role_title,
                department=department,
                seniority_level=seniority_level,
                employee_id=employee_id,
                custom_requirements=custom_requirements,
                custom_filters=custom_filters
            )
            
            # Validate curriculum completeness
            validation_results = curriculum.validate_curriculum_completeness()
            
            if not all(validation_results.values()):
                logger.warning(f"Curriculum validation issues: {validation_results}")
            
            logger.info(
                f"Successfully generated curriculum with {len(curriculum.get_all_sources())} "
                f"sources and {curriculum.total_estimated_hours:.1f} hours of content"
            )
            
            return curriculum
            
        except Exception as e:
            logger.error(f"Failed to generate curriculum: {e}")
            raise RuntimeError(f"Curriculum generation failed: {e}")
    
    async def update_document(
        self,
        document_id: str,
        document_path: str
    ) -> Dict[str, Any]:
        """
        Update a specific document in the knowledge base.
        
        Args:
            document_id: ID of document to update
            document_path: Path to updated document
            
        Returns:
            Update results
        """
        
        await self.initialize()
        
        logger.info(f"Updating document {document_id}")
        
        # Process updated document
        processed_docs = await self.document_processor.process_documents(
            [document_path],
            force_reprocess=True
        )
        
        if not processed_docs:
            return {
                'success': False,
                'message': "Failed to process updated document"
            }
        
        updated_doc = processed_docs[0]
        
        # Update in retriever
        await self.retriever.update_document(document_id, updated_doc)
        
        # Save indices
        index_path = Path(self.config.index_path) / "dual_retriever"
        self.retriever.save_indices(str(index_path))
        
        logger.info(f"Successfully updated document {document_id}")
        
        return {
            'success': True,
            'document_id': document_id,
            'updated_at': datetime.now().isoformat()
        }
    
    async def search_documents(
        self,
        query: str,
        filters: Optional[FilterCriteria] = None,
        top_k: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Search documents in the knowledge base.
        
        Args:
            query: Search query
            filters: Optional filtering criteria
            top_k: Number of results to return
            
        Returns:
            Search results with sources and scores
        """
        
        await self.initialize()
        
        if not self._documents_loaded:
            raise ValueError("No documents loaded")
        
        # Retrieve documents
        results = await self.retriever.retrieve(
            query=query,
            filters=filters,
            top_k=top_k
        )
        
        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append({
                'content': result.content[:500] + "..." if len(result.content) > 500 else result.content,
                'source': result.source.dict(),
                'relevance_score': result.relevance_score,
                'metadata': result.metadata
            })
        
        return formatted_results
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive statistics about the agent."""
        
        stats = {
            'initialized': self._initialized,
            'documents_loaded': self._documents_loaded,
            'config': {
                'llm_model': self.config.llm.model_name,
                'semantic_model': self.config.retriever.semantic_model,
                'fusion_method': self.config.retriever.fusion_method
            }
        }
        
        if self._documents_loaded:
            stats['retriever'] = self.retriever.get_stats()
        
        return stats
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform a health check of all components."""
        
        health = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'components': {}
        }
        
        try:
            # Check initialization
            health['components']['agent'] = {
                'status': 'healthy' if self._initialized else 'not_initialized',
                'documents_loaded': self._documents_loaded
            }
            
            # Check retriever
            if self._documents_loaded:
                retriever_stats = self.retriever.get_stats()
                health['components']['retriever'] = {
                    'status': 'healthy',
                    'total_documents': retriever_stats.get('semantic_retriever', {}).get('total_documents', 0)
                }
            else:
                health['components']['retriever'] = {
                    'status': 'no_documents'
                }
            
            # Check LLM (basic check)
            health['components']['llm'] = {
                'status': 'configured' if self.config.llm.api_key else 'not_configured',
                'model': self.config.llm.model_name
            }
            
            # Check curriculum generator
            health['components']['curriculum_generator'] = {
                'status': 'healthy' if hasattr(self, 'curriculum_generator') else 'not_initialized'
            }
            
        except Exception as e:
            health['status'] = 'unhealthy'
            health['error'] = str(e)
        
        return health
    
    async def close(self) -> None:
        """Clean up resources."""
        
        logger.info("Shutting down Proactive RAG Onboarding Agent")
        
        # Save indices if needed
        if self._documents_loaded:
            index_path = Path(self.config.index_path) / "dual_retriever"
            try:
                self.retriever.save_indices(str(index_path))
            except Exception as e:
                logger.warning(f"Failed to save indices during shutdown: {e}")
        
        logger.info("Agent shutdown complete")