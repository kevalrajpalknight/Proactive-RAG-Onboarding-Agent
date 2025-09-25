"""Export utilities for curriculum plans."""

import json
from typing import Dict, Any
from pathlib import Path
from datetime import datetime

from ..models import CurriculumPlan


def export_curriculum_to_markdown(
    curriculum: CurriculumPlan,
    output_path: str,
    include_sources: bool = True
) -> str:
    """
    Export curriculum to a formatted Markdown file.
    
    Args:
        curriculum: Curriculum plan to export
        output_path: Path to save the markdown file
        include_sources: Whether to include source citations
        
    Returns:
        Path to the exported file
    """
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # Header
        f.write(f"# 30-Day Onboarding Curriculum\n\n")
        f.write(f"**Role:** {curriculum.role_title}\n")
        f.write(f"**Department:** {curriculum.department}\n")
        f.write(f"**Seniority Level:** {curriculum.seniority_level}\n")
        f.write(f"**Start Date:** {curriculum.start_date.strftime('%B %d, %Y')}\n")
        f.write(f"**Total Estimated Hours:** {curriculum.total_estimated_hours:.1f}\n\n")
        
        if curriculum.employee_id:
            f.write(f"**Employee ID:** {curriculum.employee_id}\n\n")
        
        # Quality metrics
        f.write("## Quality Metrics\n\n")
        f.write(f"- **Confidence Score:** {curriculum.confidence_score:.2f}\n")
        f.write(f"- **Source Coverage:** {curriculum.source_coverage:.2f}\n")
        f.write(f"- **Total Sources:** {len(curriculum.get_all_sources())}\n\n")
        
        # Weekly modules
        for week in curriculum.weekly_modules:
            f.write(f"## Week {week.week_number}: {week.title}\n\n")
            f.write(f"**Description:** {week.description}\n\n")
            
            if week.learning_goals:
                f.write("### Learning Goals\n\n")
                for goal in week.learning_goals:
                    f.write(f"- {goal}\n")
                f.write("\n")
            
            if week.key_milestones:
                f.write("### Key Milestones\n\n")
                for milestone in week.key_milestones:
                    f.write(f"- {milestone}\n")
                f.write("\n")
            
            # Daily tasks
            f.write("### Daily Schedule\n\n")
            
            for day in ['monday', 'tuesday', 'wednesday', 'thursday', 'friday']:
                if day in week.daily_tasks and week.daily_tasks[day]:
                    f.write(f"#### {day.title()}\n\n")
                    
                    for task in week.daily_tasks[day]:
                        f.write(f"**{task.title}** ({task.estimated_duration_minutes} min)\n")
                        f.write(f"- **Type:** {task.task_type.value.title()}\n")
                        f.write(f"- **Priority:** {task.priority.value.title()}\n")
                        f.write(f"- **Description:** {task.description}\n")
                        
                        if task.learning_objectives:
                            f.write("- **Learning Objectives:**\n")
                            for obj in task.learning_objectives:
                                f.write(f"  - {obj}\n")
                        
                        if task.resources_required:
                            f.write("- **Resources Required:**\n")
                            for resource in task.resources_required:
                                f.write(f"  - {resource}\n")
                        
                        if task.deliverables:
                            f.write("- **Deliverables:**\n")
                            for deliverable in task.deliverables:
                                f.write(f"  - {deliverable}\n")
                        
                        if include_sources and task.sources:
                            f.write("- **Sources:**\n")
                            for source in task.sources:
                                f.write(f"  - [{source.title}]")
                                if source.url:
                                    f.write(f"({source.url})")
                                elif source.file_path:
                                    f.write(f"({source.file_path})")
                                f.write("\n")
                        
                        f.write("\n")
            
            if week.assessment_criteria:
                f.write("### Assessment Criteria\n\n")
                for criteria in week.assessment_criteria:
                    f.write(f"- {criteria}\n")
                f.write("\n")
        
        # Sources section
        if include_sources:
            all_sources = curriculum.get_all_sources()
            if all_sources:
                f.write("## Source References\n\n")
                
                for i, source in enumerate(all_sources, 1):
                    f.write(f"{i}. **{source.title}**\n")
                    f.write(f"   - Type: {source.document_type}\n")
                    if source.department:
                        f.write(f"   - Department: {source.department}\n")
                    if source.url:
                        f.write(f"   - URL: {source.url}\n")
                    elif source.file_path:
                        f.write(f"   - File: {source.file_path}\n")
                    if source.last_updated:
                        f.write(f"   - Last Updated: {source.last_updated.strftime('%Y-%m-%d')}\n")
                    f.write(f"   - Relevance Score: {source.relevance_score:.2f}\n")
                    f.write(f"   - Confidence Score: {source.confidence_score:.2f}\n")
                    f.write("\n")
        
        # Footer
        f.write("---\n\n")
        f.write(f"*Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}*\n")
        f.write(f"*by Proactive RAG Onboarding Agent*\n")
    
    return str(output_path)


def export_curriculum_to_json(
    curriculum: CurriculumPlan,
    output_path: str,
    pretty: bool = True
) -> str:
    """
    Export curriculum to JSON format.
    
    Args:
        curriculum: Curriculum plan to export
        output_path: Path to save the JSON file
        pretty: Whether to format JSON with indentation
        
    Returns:
        Path to the exported file
    """
    
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Convert to dictionary
    curriculum_dict = curriculum.dict()
    
    # Add export metadata
    curriculum_dict['export_metadata'] = {
        'exported_at': datetime.now().isoformat(),
        'exported_by': 'Proactive RAG Onboarding Agent',
        'format_version': '1.0'
    }
    
    # Write to file
    with open(output_path, 'w', encoding='utf-8') as f:
        if pretty:
            json.dump(curriculum_dict, f, indent=2, default=str, ensure_ascii=False)
        else:
            json.dump(curriculum_dict, f, default=str, ensure_ascii=False)
    
    return str(output_path)


def export_curriculum_summary(curriculum: CurriculumPlan) -> Dict[str, Any]:
    """
    Generate a summary of the curriculum for quick overview.
    
    Args:
        curriculum: Curriculum plan to summarize
        
    Returns:
        Summary dictionary
    """
    
    # Count tasks by type
    task_type_counts = {}
    all_task_durations = []
    
    for week in curriculum.weekly_modules:
        for day_tasks in week.daily_tasks.values():
            for task in day_tasks:
                task_type = task.task_type.value
                task_type_counts[task_type] = task_type_counts.get(task_type, 0) + 1
                all_task_durations.append(task.estimated_duration_minutes)
    
    # Calculate statistics
    total_tasks = sum(task_type_counts.values())
    avg_task_duration = sum(all_task_durations) / len(all_task_durations) if all_task_durations else 0
    
    # Count sources by type
    all_sources = curriculum.get_all_sources()
    source_type_counts = {}
    for source in all_sources:
        source_type = source.document_type
        source_type_counts[source_type] = source_type_counts.get(source_type, 0) + 1
    
    # Week-by-week breakdown
    weekly_breakdown = []
    for week in curriculum.weekly_modules:
        week_tasks = 0
        week_hours = 0
        
        for day_tasks in week.daily_tasks.values():
            week_tasks += len(day_tasks)
            week_hours += sum(task.estimated_duration_minutes for task in day_tasks) / 60
        
        weekly_breakdown.append({
            'week': week.week_number,
            'title': week.title,
            'tasks': week_tasks,
            'hours': round(week_hours, 1),
            'learning_goals': len(week.learning_goals),
            'milestones': len(week.key_milestones)
        })
    
    return {
        'curriculum_info': {
            'role_title': curriculum.role_title,
            'department': curriculum.department,
            'seniority_level': curriculum.seniority_level,
            'total_hours': curriculum.total_estimated_hours,
            'confidence_score': curriculum.confidence_score,
            'source_coverage': curriculum.source_coverage
        },
        'task_summary': {
            'total_tasks': total_tasks,
            'avg_duration_minutes': round(avg_task_duration, 1),
            'task_types': task_type_counts
        },
        'source_summary': {
            'total_sources': len(all_sources),
            'source_types': source_type_counts,
            'avg_relevance_score': round(
                sum(s.relevance_score for s in all_sources) / len(all_sources), 2
            ) if all_sources else 0
        },
        'weekly_breakdown': weekly_breakdown,
        'validation_summary': curriculum.validate_curriculum_completeness()
    }