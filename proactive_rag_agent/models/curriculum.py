"""Curriculum data models with Pydantic validation."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator

from .source import SourceCitation


class TaskType(str, Enum):
    """Types of tasks in the curriculum."""
    READING = "reading"
    TRAINING = "training"
    MEETING = "meeting"
    HANDS_ON = "hands_on"
    ASSESSMENT = "assessment"
    SHADOWING = "shadowing"


class Priority(str, Enum):
    """Task priority levels."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DailyTask(BaseModel):
    """A single task within a day of the curriculum."""
    
    title: str = Field(..., description="Task title")
    description: str = Field(..., description="Detailed task description")
    task_type: TaskType = Field(..., description="Type of task")
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")
    estimated_duration_minutes: int = Field(
        ..., ge=5, le=480, description="Estimated duration in minutes"
    )
    learning_objectives: List[str] = Field(
        default_factory=list, description="Learning objectives for this task"
    )
    resources_required: List[str] = Field(
        default_factory=list, description="Resources needed for the task"
    )
    deliverables: List[str] = Field(
        default_factory=list, description="Expected deliverables"
    )
    sources: List[SourceCitation] = Field(
        default_factory=list, description="Source citations for this task"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @validator('estimated_duration_minutes')
    def validate_duration(cls, v):
        """Validate duration is reasonable."""
        if v < 5:
            raise ValueError("Duration must be at least 5 minutes")
        if v > 480:  # 8 hours
            raise ValueError("Duration cannot exceed 8 hours (480 minutes)")
        return v


class WeeklyModule(BaseModel):
    """A weekly module containing daily tasks."""
    
    week_number: int = Field(..., ge=1, le=4, description="Week number (1-4)")
    title: str = Field(..., description="Module title")
    description: str = Field(..., description="Module description")
    learning_goals: List[str] = Field(
        default_factory=list, description="Weekly learning goals"
    )
    daily_tasks: Dict[str, List[DailyTask]] = Field(
        default_factory=dict, description="Tasks organized by day"
    )
    assessment_criteria: List[str] = Field(
        default_factory=list, description="How progress will be assessed"
    )
    key_milestones: List[str] = Field(
        default_factory=list, description="Key milestones for the week"
    )
    
    @validator('daily_tasks')
    def validate_daily_tasks(cls, v):
        """Validate daily tasks structure."""
        valid_days = {'monday', 'tuesday', 'wednesday', 'thursday', 'friday'}
        for day in v.keys():
            if day.lower() not in valid_days:
                raise ValueError(f"Invalid day: {day}. Must be one of {valid_days}")
        return v


class CurriculumPlan(BaseModel):
    """Complete 30-day curriculum plan with validation and source citations."""
    
    employee_id: Optional[str] = Field(None, description="Employee identifier")
    role_title: str = Field(..., description="Target role title")
    department: str = Field(..., description="Department")
    seniority_level: str = Field(..., description="Seniority level")
    start_date: datetime = Field(
        default_factory=datetime.now, description="Curriculum start date"
    )
    
    # Core curriculum structure
    weekly_modules: List[WeeklyModule] = Field(
        ..., min_items=4, max_items=4, description="Four weekly modules"
    )
    
    # Meta information
    total_estimated_hours: float = Field(
        0.0, ge=0, description="Total estimated hours for the curriculum"
    )
    primary_sources: List[SourceCitation] = Field(
        default_factory=list, description="Primary sources used in curriculum generation"
    )
    
    # Customization metadata  
    customization_factors: Dict[str, Any] = Field(
        default_factory=dict, description="Factors used for customization"
    )
    generated_at: datetime = Field(
        default_factory=datetime.now, description="When the curriculum was generated"
    )
    
    # Validation and quality metrics
    confidence_score: float = Field(
        0.0, ge=0.0, le=1.0, description="Confidence in curriculum quality"
    )
    source_coverage: float = Field(
        0.0, ge=0.0, le=1.0, description="Percentage of sources that contributed"
    )
    
    def calculate_total_hours(self) -> float:
        """Calculate total estimated hours across all tasks."""
        total_minutes = 0
        for week in self.weekly_modules:
            for day_tasks in week.daily_tasks.values():
                for task in day_tasks:
                    total_minutes += task.estimated_duration_minutes
        return total_minutes / 60.0
    
    def get_all_sources(self) -> List[SourceCitation]:
        """Get all unique source citations from the curriculum."""
        all_sources = list(self.primary_sources)
        for week in self.weekly_modules:
            for day_tasks in week.daily_tasks.values():
                for task in day_tasks:
                    all_sources.extend(task.sources)
        
        # Remove duplicates based on source_id
        unique_sources = {}
        for source in all_sources:
            unique_sources[source.source_id] = source
        
        return list(unique_sources.values())
    
    def validate_curriculum_completeness(self) -> Dict[str, bool]:
        """Validate that the curriculum meets completeness requirements."""
        checks = {
            "has_four_weeks": len(self.weekly_modules) == 4,
            "all_weeks_have_tasks": all(
                len(week.daily_tasks) > 0 for week in self.weekly_modules
            ),
            "has_sources": len(self.get_all_sources()) > 0,
            "reasonable_duration": 80 <= self.calculate_total_hours() <= 200,
            "has_assessments": any(
                any(
                    task.task_type == TaskType.ASSESSMENT 
                    for day_tasks in week.daily_tasks.values()
                    for task in day_tasks
                )
                for week in self.weekly_modules
            )
        }
        return checks

    @validator('weekly_modules')
    def validate_four_weeks(cls, v):
        """Ensure exactly 4 weeks are provided."""
        if len(v) != 4:
            raise ValueError("Curriculum must have exactly 4 weekly modules")
        
        # Validate week numbers are 1, 2, 3, 4
        week_numbers = [week.week_number for week in v]
        if sorted(week_numbers) != [1, 2, 3, 4]:
            raise ValueError("Week numbers must be 1, 2, 3, 4")
        
        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization to calculate derived fields."""
        if self.total_estimated_hours == 0.0:
            self.total_estimated_hours = self.calculate_total_hours()