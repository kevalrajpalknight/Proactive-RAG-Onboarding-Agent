"""Document processing and ingestion utilities."""

import asyncio
import logging
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import hashlib
import json
from datetime import datetime
import mimetypes

import pandas as pd
from langchain_community.document_loaders import (
    TextLoader, PyPDFLoader, UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader, UnstructuredPowerPointLoader,
    DirectoryLoader, UnstructuredHTMLLoader
)
from langchain.text_splitter import RecursiveCharacterTextSplitter

from ..config import AgentConfig
from ..models.metadata import DocumentMetadata, DocumentType, AccessLevel


logger = logging.getLogger(__name__)


class DocumentProcessor:
    """
    Document processing and ingestion pipeline.
    
    Handles loading, preprocessing, and metadata extraction from various
    document formats for the knowledge base.
    """
    
    def __init__(self, config: AgentConfig):
        """
        Initialize document processor.
        
        Args:
            config: Agent configuration
        """
        self.config = config
        
        # Initialize text splitter
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""]
        )
        
        # Document type mapping based on file extensions
        self.extension_to_type = {
            '.pdf': DocumentType.MANUAL,
            '.doc': DocumentType.GUIDE,
            '.docx': DocumentType.GUIDE,
            '.txt': DocumentType.GUIDE,
            '.md': DocumentType.GUIDE,
            '.html': DocumentType.GUIDE,
            '.htm': DocumentType.GUIDE,
            '.xls': DocumentType.TEMPLATE,
            '.xlsx': DocumentType.TEMPLATE,
            '.ppt': DocumentType.PRESENTATION,
            '.pptx': DocumentType.PRESENTATION,
            '.json': DocumentType.OTHER,
            '.yaml': DocumentType.OTHER,
            '.yml': DocumentType.OTHER,
        }
        
        # Cache for processed documents
        self._processed_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_file = Path(self.config.cache_path) / "document_cache.json"
        
        # Load existing cache
        self._load_cache()
    
    async def process_documents(
        self,
        document_paths: List[str],
        force_reprocess: bool = False,
        batch_size: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Process multiple documents or directories.
        
        Args:
            document_paths: List of file or directory paths
            force_reprocess: Force reprocessing even if cached
            batch_size: Number of documents to process concurrently
            
        Returns:
            List of processed document data
        """
        
        logger.info(f"Processing {len(document_paths)} document paths")
        
        # Collect all files to process
        all_files = []
        for path_str in document_paths:
            path = Path(path_str)
            if path.is_file():
                all_files.append(path)
            elif path.is_dir():
                all_files.extend(self._collect_files_from_directory(path))
            else:
                logger.warning(f"Path not found: {path}")
        
        logger.info(f"Found {len(all_files)} files to process")
        
        # Filter files that need processing
        files_to_process = []
        for file_path in all_files:
            if force_reprocess or not self._is_cached(file_path):
                files_to_process.append(file_path)
        
        logger.info(f"Processing {len(files_to_process)} files (others cached)")
        
        # Process files in batches
        processed_docs = []
        for i in range(0, len(files_to_process), batch_size):
            batch = files_to_process[i:i + batch_size]
            batch_results = await self._process_batch(batch)
            processed_docs.extend(batch_results)
        
        # Add cached documents
        for file_path in all_files:
            if file_path not in files_to_process:
                cached_doc = self._get_cached_document(file_path)
                if cached_doc:
                    processed_docs.append(cached_doc)
        
        # Save cache
        self._save_cache()
        
        logger.info(f"Successfully processed {len(processed_docs)} documents")
        return processed_docs
    
    async def process_single_document(
        self,
        file_path: str,
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Process a single document.
        
        Args:
            file_path: Path to the document
            custom_metadata: Optional custom metadata
            
        Returns:
            Processed document data or None if failed
        """
        
        path = Path(file_path)
        
        if not path.exists():
            logger.error(f"File not found: {path}")
            return None
        
        try:
            # Load document content
            content = await self._load_document_content(path)
            if not content:
                logger.warning(f"No content extracted from {path}")
                return None
            
            # Extract metadata
            metadata = self._extract_metadata(path, content, custom_metadata)
            
            # Create document data
            doc_data = {
                'id': self._generate_document_id(path),
                'title': self._extract_title(path, content),
                'content': content,
                'file_path': str(path),
                'url': None,
                'metadata': metadata.dict(),
                'processed_at': datetime.now().isoformat(),
                'extra_metadata': custom_metadata or {}
            }
            
            # Cache the result
            self._cache_document(path, doc_data)
            
            return doc_data
            
        except Exception as e:
            logger.error(f"Failed to process document {path}: {e}")
            return None
    
    def _collect_files_from_directory(self, directory: Path) -> List[Path]:
        """Collect supported files from a directory recursively."""
        
        supported_extensions = set(self.extension_to_type.keys())
        files = []
        
        for item in directory.rglob("*"):
            if item.is_file() and item.suffix.lower() in supported_extensions:
                files.append(item)
        
        return files
    
    async def _process_batch(self, file_paths: List[Path]) -> List[Dict[str, Any]]:
        """Process a batch of files concurrently."""
        
        tasks = [
            self.process_single_document(str(path))
            for path in file_paths
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Filter successful results
        processed_docs = []
        for result in results:
            if isinstance(result, dict):
                processed_docs.append(result)
            elif isinstance(result, Exception):
                logger.error(f"Batch processing error: {result}")
        
        return processed_docs
    
    async def _load_document_content(self, file_path: Path) -> Optional[str]:
        """Load content from a document file."""
        
        try:
            file_extension = file_path.suffix.lower()
            
            # Choose appropriate loader based on file type
            if file_extension == '.pdf':
                loader = PyPDFLoader(str(file_path))
            elif file_extension in ['.doc', '.docx']:
                loader = UnstructuredWordDocumentLoader(str(file_path))
            elif file_extension in ['.xls', '.xlsx']:
                loader = UnstructuredExcelLoader(str(file_path))
            elif file_extension in ['.ppt', '.pptx']:
                loader = UnstructuredPowerPointLoader(str(file_path))
            elif file_extension in ['.html', '.htm']:
                loader = UnstructuredHTMLLoader(str(file_path))
            elif file_extension in ['.txt', '.md']:
                loader = TextLoader(str(file_path), encoding='utf-8')
            else:
                # Try as text file
                loader = TextLoader(str(file_path), encoding='utf-8')
            
            # Load documents
            documents = await asyncio.get_event_loop().run_in_executor(
                None, loader.load
            )
            
            if not documents:
                return None
            
            # Combine content from all pages/sections
            content = "\n\n".join([doc.page_content for doc in documents])
            
            # Clean up content
            content = self._clean_content(content)
            
            return content
            
        except Exception as e:
            logger.error(f"Failed to load content from {file_path}: {e}")
            return None
    
    def _clean_content(self, content: str) -> str:
        """Clean and normalize document content."""
        
        if not content:
            return ""
        
        # Remove excessive whitespace
        content = " ".join(content.split())
        
        # Remove very short lines (likely artifacts)
        lines = content.split('\n')
        cleaned_lines = [
            line.strip() for line in lines 
            if len(line.strip()) > 10 or line.strip().endswith('.')
        ]
        
        content = '\n'.join(cleaned_lines)
        
        # Limit content length (for very large documents)
        max_length = 50000  # ~50k characters
        if len(content) > max_length:
            content = content[:max_length] + "\n[Content truncated...]"
        
        return content.strip()
    
    def _extract_metadata(
        self,
        file_path: Path,
        content: str,
        custom_metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentMetadata:
        """Extract metadata from document."""
        
        # Basic metadata
        file_stats = file_path.stat()
        
        # Determine document type
        doc_type = self.extension_to_type.get(
            file_path.suffix.lower(), 
            DocumentType.OTHER
        )
        
        # Extract topics and keywords from content
        topics = self._extract_topics(content)
        keywords = self._extract_keywords(content)
        
        # Try to extract department and role information
        department = self._extract_department(file_path.name, content)
        target_roles = self._extract_target_roles(content)
        
        # Calculate reading time (average 200 words per minute)
        word_count = len(content.split())
        reading_time = max(5, word_count // 200)  # Minimum 5 minutes
        
        # Determine importance based on file characteristics
        importance_score = self._calculate_importance_score(
            file_path, content, doc_type
        )
        
        metadata = DocumentMetadata(
            document_id=self._generate_document_id(file_path),
            title=self._extract_title(file_path, content),
            document_type=doc_type,
            description=self._extract_description(content),
            topics=topics,
            keywords=keywords,
            department=department,
            target_roles=target_roles,
            created_date=datetime.fromtimestamp(file_stats.st_ctime),
            last_updated=datetime.fromtimestamp(file_stats.st_mtime),
            word_count=word_count,
            reading_time_minutes=reading_time,
            importance_score=importance_score,
            popularity_score=0.5,  # Default, could be updated based on usage
            access_level=AccessLevel.INTERNAL,  # Default
        )
        
        # Apply custom metadata if provided
        if custom_metadata:
            for key, value in custom_metadata.items():
                if hasattr(metadata, key):
                    setattr(metadata, key, value)
                else:
                    metadata.custom_metadata[key] = value
        
        return metadata
    
    def _extract_title(self, file_path: Path, content: str) -> str:
        """Extract document title."""
        
        # Try to find title in content (first line or heading)
        lines = content.split('\n')
        for line in lines[:5]:  # Check first 5 lines
            line = line.strip()
            if len(line) > 5 and len(line) < 100:
                # Remove common heading markers
                line = line.lstrip('#').strip()
                if line:
                    return line
        
        # Fallback to filename
        return file_path.stem.replace('_', ' ').replace('-', ' ').title()
    
    def _extract_description(self, content: str) -> str:
        """Extract document description from content."""
        
        # Use first paragraph as description
        paragraphs = content.split('\n\n')
        for paragraph in paragraphs[:3]:
            paragraph = paragraph.strip()
            if 20 <= len(paragraph) <= 300:  # Reasonable description length
                return paragraph
        
        # Fallback to first 200 characters
        return content[:200].strip() + "..." if len(content) > 200 else content
    
    def _extract_topics(self, content: str) -> List[str]:
        """Extract topics from content using simple keyword matching."""
        
        # Common business/corporate topics
        topic_keywords = {
            'hr': ['human resources', 'hr policy', 'employee', 'hiring', 'benefits'],
            'it': ['technology', 'software', 'system', 'network', 'security'],
            'finance': ['budget', 'financial', 'accounting', 'expense', 'cost'],
            'marketing': ['marketing', 'promotion', 'advertising', 'brand', 'campaign'],
            'sales': ['sales', 'customer', 'client', 'revenue', 'quota'],
            'operations': ['process', 'procedure', 'workflow', 'operation', 'quality'],
            'compliance': ['compliance', 'regulation', 'audit', 'legal', 'policy'],
            'training': ['training', 'learning', 'development', 'skill', 'education'],
            'onboarding': ['onboarding', 'orientation', 'new hire', 'welcome', 'introduction']
        }
        
        content_lower = content.lower()
        detected_topics = []
        
        for topic, keywords in topic_keywords.items():
            if any(keyword in content_lower for keyword in keywords):
                detected_topics.append(topic)
        
        return detected_topics[:5]  # Limit to top 5 topics
    
    def _extract_keywords(self, content: str) -> List[str]:
        """Extract keywords from content."""
        
        # Simple keyword extraction - find frequently used meaningful words
        words = content.lower().split()
        
        # Filter out common words and short words
        stop_words = {
            'the', 'a', 'an', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for',
            'of', 'with', 'by', 'from', 'up', 'about', 'into', 'through', 'during',
            'before', 'after', 'above', 'below', 'over', 'under', 'again', 'further',
            'then', 'once', 'here', 'there', 'when', 'where', 'why', 'how', 'all',
            'any', 'both', 'each', 'few', 'more', 'most', 'other', 'some', 'such',
            'no', 'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            'can', 'will', 'just', 'should', 'now', 'is', 'are', 'was', 'were'
        }
        
        meaningful_words = [
            word.strip('.,!?;:"()[]{}') for word in words 
            if len(word) > 3 and word not in stop_words and word.isalpha()
        ]
        
        # Count frequency
        word_freq = {}
        for word in meaningful_words:
            word_freq[word] = word_freq.get(word, 0) + 1
        
        # Get top keywords
        sorted_words = sorted(word_freq.items(), key=lambda x: x[1], reverse=True)
        keywords = [word for word, freq in sorted_words[:10] if freq > 1]
        
        return keywords
    
    def _extract_department(self, filename: str, content: str) -> Optional[str]:
        """Try to extract department from filename or content."""
        
        departments = [
            'hr', 'human resources', 'it', 'information technology', 'finance',
            'marketing', 'sales', 'operations', 'legal', 'compliance',
            'engineering', 'product', 'design', 'research', 'support'
        ]
        
        text_to_check = f"{filename} {content[:500]}".lower()
        
        for dept in departments:
            if dept in text_to_check:
                return dept.title()
        
        return None
    
    def _extract_target_roles(self, content: str) -> List[str]:
        """Extract target roles from content."""
        
        common_roles = [
            'manager', 'developer', 'analyst', 'coordinator', 'specialist',
            'administrator', 'director', 'associate', 'consultant', 'engineer',
            'designer', 'representative', 'lead', 'supervisor', 'executive'
        ]
        
        content_lower = content.lower()
        found_roles = []
        
        for role in common_roles:
            if role in content_lower:
                found_roles.append(role.title())
        
        return list(set(found_roles))[:5]  # Unique roles, max 5
    
    def _calculate_importance_score(
        self, file_path: Path, content: str, doc_type: DocumentType
    ) -> float:
        """Calculate importance score based on document characteristics."""
        
        score = 0.5  # Base score
        
        # Document type importance
        type_scores = {
            DocumentType.POLICY: 0.9,
            DocumentType.PROCEDURE: 0.8,
            DocumentType.MANUAL: 0.7,
            DocumentType.GUIDE: 0.6,
            DocumentType.TRAINING: 0.8,
            DocumentType.FAQ: 0.5,
            DocumentType.TEMPLATE: 0.4,
            DocumentType.PRESENTATION: 0.5,
            DocumentType.OTHER: 0.3
        }
        score = type_scores.get(doc_type, 0.5)
        
        # Content length bonus (more comprehensive documents)
        word_count = len(content.split())
        if word_count > 2000:
            score += 0.1
        elif word_count > 1000:
            score += 0.05
        
        # Recent update bonus
        if file_path.exists():
            days_old = (datetime.now() - datetime.fromtimestamp(file_path.stat().st_mtime)).days
            if days_old < 30:
                score += 0.1
            elif days_old < 90:
                score += 0.05
        
        return min(score, 1.0)
    
    def _generate_document_id(self, file_path: Path) -> str:
        """Generate unique document ID."""
        return hashlib.md5(str(file_path).encode()).hexdigest()
    
    def _is_cached(self, file_path: Path) -> bool:
        """Check if document is cached and up-to-date."""
        
        doc_id = self._generate_document_id(file_path)
        if doc_id not in self._processed_cache:
            return False
        
        cached_doc = self._processed_cache[doc_id]
        cached_mtime = cached_doc.get('file_mtime')
        
        if not cached_mtime:
            return False
        
        current_mtime = file_path.stat().st_mtime
        return abs(current_mtime - cached_mtime) < 1  # 1 second tolerance
    
    def _get_cached_document(self, file_path: Path) -> Optional[Dict[str, Any]]:
        """Get cached document data."""
        
        doc_id = self._generate_document_id(file_path)
        cached_doc = self._processed_cache.get(doc_id)
        
        if cached_doc:
            # Return a copy without cache-specific metadata
            doc_data = cached_doc.copy()
            doc_data.pop('file_mtime', None)
            return doc_data
        
        return None
    
    def _cache_document(self, file_path: Path, doc_data: Dict[str, Any]) -> None:
        """Cache processed document data."""
        
        doc_id = self._generate_document_id(file_path)
        
        # Add cache metadata
        cached_doc = doc_data.copy()
        cached_doc['file_mtime'] = file_path.stat().st_mtime
        
        self._processed_cache[doc_id] = cached_doc
    
    def _load_cache(self) -> None:
        """Load document cache from disk."""
        
        try:
            if self._cache_file.exists():
                with open(self._cache_file, 'r') as f:
                    self._processed_cache = json.load(f)
                logger.info(f"Loaded {len(self._processed_cache)} cached documents")
        except Exception as e:
            logger.warning(f"Failed to load document cache: {e}")
            self._processed_cache = {}
    
    def _save_cache(self) -> None:
        """Save document cache to disk."""
        
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._cache_file, 'w') as f:
                json.dump(self._processed_cache, f, default=str, indent=2)
            logger.debug(f"Saved {len(self._processed_cache)} documents to cache")
        except Exception as e:
            logger.warning(f"Failed to save document cache: {e}")
    
    def clear_cache(self) -> None:
        """Clear the document cache."""
        
        self._processed_cache.clear()
        if self._cache_file.exists():
            self._cache_file.unlink()
        logger.info("Document cache cleared")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get processing statistics."""
        
        return {
            'cached_documents': len(self._processed_cache),
            'supported_extensions': list(self.extension_to_type.keys()),
            'cache_file': str(self._cache_file)
        }