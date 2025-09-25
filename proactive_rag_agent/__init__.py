"""
Proactive RAG Onboarding Agent

A system for generating tailored 30-day curricula for new hires using
LangChain with dual-retriever architecture and metadata filtering.
"""

__version__ = "0.1.0"
__author__ = "Keval Raj Palknight"

# Import core models without dependencies for basic usage
from .models.curriculum import CurriculumPlan, DailyTask, WeeklyModule
from .models.metadata import DocumentMetadata, FilterCriteria
from .models.source import SourceCitation

__all__ = [
    "CurriculumPlan", 
    "DailyTask",
    "WeeklyModule",
    "DocumentMetadata",
    "FilterCriteria",
    "SourceCitation",
]

# Optional imports that require dependencies
def get_onboarding_agent():
    """Get OnboardingAgent (requires all dependencies to be installed)."""
    from .core.agent import OnboardingAgent
    return OnboardingAgent