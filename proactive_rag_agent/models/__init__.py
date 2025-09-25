"""Data models for the Proactive RAG Onboarding Agent."""

from .curriculum import CurriculumPlan, DailyTask, WeeklyModule
from .metadata import DocumentMetadata, FilterCriteria
from .source import SourceCitation, CitedContent

__all__ = [
    "CurriculumPlan",
    "DailyTask", 
    "WeeklyModule",
    "DocumentMetadata",
    "FilterCriteria",
    "SourceCitation",
    "CitedContent",
]