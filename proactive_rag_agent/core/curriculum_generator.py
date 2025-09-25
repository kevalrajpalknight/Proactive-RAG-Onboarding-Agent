"""Curriculum generation using LLM and retrieved documents."""

import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
import json
import re

from langchain_openai import ChatOpenAI
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_community.callbacks import get_openai_callback

from ..config import AgentConfig
from ..retrievers.base_retriever import BaseRetriever
from ..models import (
    CurriculumPlan, WeeklyModule, DailyTask, TaskType, Priority,
    FilterCriteria, DocumentType, SourceCitation
)


logger = logging.getLogger(__name__)


class CurriculumGenerator:
    """
    Generates tailored 30-day curricula using LLM and retrieved documents.
    
    This component uses the dual retriever to find relevant content and then
    employs an LLM to structure it into a comprehensive curriculum plan.
    """
    
    def __init__(self, config: AgentConfig, retriever: BaseRetriever):
        """
        Initialize curriculum generator.
        
        Args:
            config: Agent configuration
            retriever: Retriever for finding relevant documents
        """
        self.config = config
        self.retriever = retriever
        
        # Initialize LLM
        self.llm = None
        self._initialized = False
    
    async def initialize(self) -> None:
        """Initialize the LLM and other components."""
        
        if self._initialized:
            return
        
        if not self.config.llm.api_key:
            raise ValueError("OpenAI API key is required")
        
        # Initialize ChatOpenAI
        self.llm = ChatOpenAI(
            model_name=self.config.llm.model_name,
            temperature=self.config.llm.temperature,
            max_tokens=self.config.llm.max_tokens,
            openai_api_key=self.config.llm.api_key,
            top_p=self.config.llm.top_p,
            frequency_penalty=self.config.llm.frequency_penalty,
            presence_penalty=self.config.llm.presence_penalty,
        )
        
        self._initialized = True
        logger.info("Curriculum generator initialized")
    
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
        Generate a complete 30-day curriculum plan.
        
        Args:
            role_title: Target role title
            department: Department
            seniority_level: Seniority level
            employee_id: Optional employee identifier
            custom_requirements: Additional requirements
            custom_filters: Custom filtering criteria
            
        Returns:
            Generated curriculum plan with sources
        """
        
        await self.initialize()
        
        logger.info(f"Generating curriculum for {role_title} ({seniority_level}) in {department}")
        
        # Create filter criteria
        filters = self._create_filter_criteria(
            role_title, department, seniority_level, custom_filters
        )
        
        # Generate curriculum outline
        outline = await self._generate_curriculum_outline(
            role_title, department, seniority_level, custom_requirements
        )
        
        # Generate detailed weekly modules
        weekly_modules = []
        all_sources = []
        
        for week_num in range(1, 5):  # 4 weeks
            module, sources = await self._generate_weekly_module(
                week_num, outline, role_title, department, seniority_level, filters
            )
            weekly_modules.append(module)
            all_sources.extend(sources)
        
        # Create curriculum plan
        curriculum = CurriculumPlan(
            employee_id=employee_id,
            role_title=role_title,
            department=department,
            seniority_level=seniority_level,
            start_date=datetime.now(),
            weekly_modules=weekly_modules,
            primary_sources=self._deduplicate_sources(all_sources),
            customization_factors={
                "role_title": role_title,
                "department": department,
                "seniority_level": seniority_level,
                "custom_requirements": custom_requirements or [],
                "filter_criteria": filters.dict() if filters else {}
            },
            generated_at=datetime.now()
        )
        
        # Calculate quality metrics
        curriculum.confidence_score = self._calculate_confidence_score(curriculum)
        curriculum.source_coverage = self._calculate_source_coverage(curriculum)
        
        logger.info(
            f"Generated curriculum with {len(curriculum.weekly_modules)} weeks, "
            f"{len(curriculum.get_all_sources())} sources, "
            f"confidence: {curriculum.confidence_score:.2f}"
        )
        
        return curriculum
    
    def _create_filter_criteria(
        self,
        role_title: str,
        department: str,
        seniority_level: str,
        custom_filters: Optional[FilterCriteria]
    ) -> FilterCriteria:
        """Create filter criteria for document retrieval."""
        
        if custom_filters:
            return custom_filters
        
        # Map seniority to document types
        seniority_doc_types = {
            "junior": [DocumentType.GUIDE, DocumentType.TRAINING, DocumentType.FAQ],
            "mid": [DocumentType.GUIDE, DocumentType.PROCEDURE, DocumentType.MANUAL],
            "senior": [DocumentType.POLICY, DocumentType.PROCEDURE, DocumentType.MANUAL]
        }
        
        return FilterCriteria(
            target_role=role_title,
            department=department,
            seniority_level=seniority_level,
            document_types=seniority_doc_types.get(seniority_level, []),
            max_age_days=365,  # Prefer recent documents
            min_importance_score=0.3
        )
    
    async def _generate_curriculum_outline(
        self,
        role_title: str,
        department: str,
        seniority_level: str,
        custom_requirements: Optional[List[str]]
    ) -> Dict[str, Any]:
        """Generate high-level curriculum outline."""
        
        # Retrieve general context about the role and department
        context_query = f"onboarding {role_title} {department} {seniority_level} training overview"
        context_docs = await self.retriever.retrieve(
            query=context_query,
            top_k=5
        )
        
        context_text = "\n".join([
            f"- {doc.source.title}: {doc.content[:200]}..."
            for doc in context_docs[:3]
        ])
        
        system_prompt = """You are an expert corporate onboarding specialist. Generate a structured 4-week curriculum outline for a new employee.

The outline should include:
1. Week-by-week learning objectives
2. Key topics and skills to cover
3. Suggested task types and time allocation
4. Assessment and milestone recommendations

Focus on practical, actionable learning that progresses from basic orientation to role-specific competency."""

        human_prompt = f"""Create a 4-week onboarding curriculum outline for:
- Role: {role_title}
- Department: {department}  
- Seniority Level: {seniority_level}

Context from company documents:
{context_text}

Additional Requirements:
{custom_requirements or "None specified"}

Provide a JSON structure with weeks 1-4, each containing:
- title: Week title
- objectives: List of learning objectives  
- topics: Key topics to cover
- task_distribution: Suggested percentage of different task types
- milestones: Key achievements expected
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        with get_openai_callback() as cb:
            response = await self.llm.agenerate([messages])
            logger.info(f"Outline generation cost: ${cb.total_cost:.4f}")
        
        # Parse JSON response
        try:
            outline = json.loads(response.generations[0][0].text)
            return outline
        except json.JSONDecodeError:
            # Fallback to default outline
            logger.warning("Failed to parse LLM outline, using default")
            return self._get_default_outline(role_title, department, seniority_level)
    
    async def _generate_weekly_module(
        self,
        week_number: int,
        outline: Dict[str, Any],
        role_title: str,
        department: str,
        seniority_level: str,
        filters: FilterCriteria
    ) -> tuple[WeeklyModule, List[SourceCitation]]:
        """Generate a detailed weekly module."""
        
        week_info = outline.get(f"week_{week_number}", {})
        week_title = week_info.get("title", f"Week {week_number}")
        week_objectives = week_info.get("objectives", [])
        week_topics = week_info.get("topics", [])
        
        # Retrieve relevant documents for this week
        week_query = f"{role_title} {department} week {week_number} " + " ".join(week_topics[:3])
        relevant_docs = await self.retriever.retrieve(
            query=week_query,
            filters=filters,
            top_k=15
        )
        
        # Generate daily tasks
        daily_tasks = {}
        week_sources = []
        
        days = ["monday", "tuesday", "wednesday", "thursday", "friday"]
        
        for day in days:
            tasks, day_sources = await self._generate_daily_tasks(
                week_number, day, week_info, relevant_docs, role_title, department
            )
            daily_tasks[day] = tasks
            week_sources.extend(day_sources)
        
        # Create weekly module
        module = WeeklyModule(
            week_number=week_number,
            title=week_title,
            description=week_info.get("description", f"Learning objectives for {week_title}"),
            learning_goals=week_objectives,
            daily_tasks=daily_tasks,
            assessment_criteria=week_info.get("assessment_criteria", []),
            key_milestones=week_info.get("milestones", [])
        )
        
        return module, week_sources
    
    async def _generate_daily_tasks(
        self,
        week_number: int,
        day: str,
        week_info: Dict[str, Any],
        relevant_docs: List[Any],
        role_title: str,
        department: str
    ) -> tuple[List[DailyTask], List[SourceCitation]]:
        """Generate tasks for a specific day."""
        
        # Select documents for this day (2-4 docs per day)
        docs_per_day = min(4, max(2, len(relevant_docs) // 5))
        day_docs = relevant_docs[:docs_per_day]
        
        if not day_docs:
            # Create a basic task without sources
            task = DailyTask(
                title=f"General Orientation - {day.title()}",
                description=f"Basic orientation activities for {role_title}",
                task_type=TaskType.TRAINING,
                estimated_duration_minutes=240,
                learning_objectives=[f"Complete initial setup and orientation"],
            )
            return [task], []
        
        # Create context from documents
        doc_context = "\n".join([
            f"Document: {doc.source.title}\nContent: {doc.content[:300]}...\n"
            for doc in day_docs
        ])
        
        system_prompt = f"""You are creating daily onboarding tasks for a {role_title} in {department}.

Generate 2-4 specific, actionable tasks for {day} of week {week_number}. Each task should:
1. Have a clear title and description
2. Specify appropriate task type (reading, training, meeting, hands_on, assessment, shadowing)
3. Include realistic time estimates (30-120 minutes per task)
4. List specific learning objectives
5. Mention required resources or deliverables

Make tasks practical and progressive, building on previous learning."""

        human_prompt = f"""Create tasks for {day} of week {week_number} based on these company documents:

{doc_context}

Week objectives: {week_info.get('objectives', [])}

Return a JSON array of tasks with fields:
- title: Task title
- description: Detailed description  
- task_type: Type from [reading, training, meeting, hands_on, assessment, shadowing]
- estimated_duration_minutes: Duration (30-120 minutes)
- learning_objectives: Array of specific objectives
- resources_required: Array of needed resources
- deliverables: Array of expected outputs
"""

        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=human_prompt)
        ]
        
        try:
            with get_openai_callback() as cb:
                response = await self.llm.agenerate([messages])
                logger.debug(f"Daily tasks generation cost: ${cb.total_cost:.4f}")
            
            # Parse tasks
            tasks_data = json.loads(response.generations[0][0].text)
            
            tasks = []
            sources = []
            
            for task_data in tasks_data:
                # Create task with sources
                task_sources = [doc.source for doc in day_docs]
                
                task = DailyTask(
                    title=task_data.get("title", "Untitled Task"),
                    description=task_data.get("description", ""),
                    task_type=TaskType(task_data.get("task_type", "training")),
                    priority=Priority.MEDIUM,
                    estimated_duration_minutes=task_data.get("estimated_duration_minutes", 60),
                    learning_objectives=task_data.get("learning_objectives", []),
                    resources_required=task_data.get("resources_required", []),
                    deliverables=task_data.get("deliverables", []),
                    sources=task_sources
                )
                
                tasks.append(task)
                sources.extend(task_sources)
            
            return tasks, sources
            
        except Exception as e:
            logger.warning(f"Failed to generate daily tasks: {e}")
            
            # Fallback: create basic tasks from documents
            tasks = []
            sources = []
            
            for i, doc in enumerate(day_docs):
                task = DailyTask(
                    title=f"Study: {doc.source.title}",
                    description=f"Review and understand {doc.source.title}",
                    task_type=TaskType.READING,
                    estimated_duration_minutes=60,
                    learning_objectives=[f"Understand content of {doc.source.title}"],
                    sources=[doc.source]
                )
                tasks.append(task)
                sources.append(doc.source)
            
            return tasks, sources
    
    def _get_default_outline(
        self, role_title: str, department: str, seniority_level: str
    ) -> Dict[str, Any]:
        """Get default curriculum outline when LLM generation fails."""
        
        return {
            "week_1": {
                "title": "Company Orientation and Setup",
                "objectives": [
                    "Complete initial setup and paperwork",
                    "Understand company culture and values",
                    "Meet key team members"
                ],
                "topics": ["company_overview", "policies", "tools_setup"],
                "milestones": ["Complete setup checklist", "Meet team"]
            },
            "week_2": {
                "title": "Role Introduction and Training",
                "objectives": [
                    "Understand role responsibilities",
                    "Learn key processes and procedures",
                    "Begin hands-on practice"
                ],
                "topics": ["role_specific_training", "processes", "tools"],
                "milestones": ["Complete role assessment", "Shadow experienced colleague"]
            },
            "week_3": {
                "title": "Skill Development and Practice",
                "objectives": [
                    "Develop core job skills",
                    "Complete practical exercises",
                    "Begin independent work"
                ],
                "topics": ["skill_building", "practice_projects", "feedback"],
                "milestones": ["Complete practice project", "Receive feedback"]
            },
            "week_4": {
                "title": "Integration and Assessment",
                "objectives": [
                    "Demonstrate competency",
                    "Complete final assessments",
                    "Plan ongoing development"
                ],
                "topics": ["assessment", "competency_check", "development_planning"],
                "milestones": ["Pass competency assessment", "Create development plan"]
            }
        }
    
    def _deduplicate_sources(self, sources: List[SourceCitation]) -> List[SourceCitation]:
        """Remove duplicate sources based on source_id."""
        seen = set()
        unique_sources = []
        
        for source in sources:
            if source.source_id not in seen:
                seen.add(source.source_id)
                unique_sources.append(source)
        
        return unique_sources
    
    def _calculate_confidence_score(self, curriculum: CurriculumPlan) -> float:
        """Calculate confidence score for the curriculum."""
        
        score = 0.0
        factors = 0
        
        # Factor 1: Source coverage (0.3 weight)
        unique_sources = len(curriculum.get_all_sources())
        if unique_sources >= 10:
            score += 0.3
        elif unique_sources >= 5:
            score += 0.15
        factors += 1
        
        # Factor 2: Task distribution (0.3 weight)
        all_tasks = []
        for week in curriculum.weekly_modules:
            for day_tasks in week.daily_tasks.values():
                all_tasks.extend(day_tasks)
        
        if all_tasks:
            task_types = [task.task_type for task in all_tasks]
            unique_types = len(set(task_types))
            if unique_types >= 4:
                score += 0.3
            elif unique_types >= 2:
                score += 0.15
        factors += 1
        
        # Factor 3: Time allocation (0.2 weight)
        total_hours = curriculum.calculate_total_hours()
        if 80 <= total_hours <= 200:  # Reasonable range
            score += 0.2
        elif 60 <= total_hours <= 240:
            score += 0.1
        factors += 1
        
        # Factor 4: Assessment presence (0.2 weight)
        has_assessments = any(
            any(
                task.task_type == TaskType.ASSESSMENT
                for day_tasks in week.daily_tasks.values()
                for task in day_tasks
            )
            for week in curriculum.weekly_modules
        )
        if has_assessments:
            score += 0.2
        factors += 1
        
        return min(score, 1.0)
    
    def _calculate_source_coverage(self, curriculum: CurriculumPlan) -> float:
        """Calculate what percentage of sources actually contributed content."""
        
        all_sources = curriculum.get_all_sources()
        if not all_sources:
            return 0.0
        
        # For now, assume all retrieved sources contributed
        # In a more sophisticated implementation, we'd track actual usage
        return min(1.0, len(all_sources) / 20)  # Normalize to expected ~20 sources