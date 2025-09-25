"""
Proactive RAG Onboarding Agent

A system for generating tailored 30-day curricula for new hires using
LangChain with dual-retriever architecture and metadata filtering.
"""

__version__ = "0.1.0"
__author__ = "Keval Raj Palknight"

from .core.agent import OnboardingAgent
from .models.curriculum import CurriculumPlan, DailyTask, WeeklyModule
from .models.metadata import DocumentMetadata, FilterCriteria

__all__ = [
    "OnboardingAgent",
    "CurriculumPlan", 
    "DailyTask",
    "WeeklyModule",
    "DocumentMetadata",
    "FilterCriteria",
]