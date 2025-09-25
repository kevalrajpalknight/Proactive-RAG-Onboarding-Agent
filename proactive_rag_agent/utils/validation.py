"""Validation utilities for curriculum and sources."""

from typing import Dict, List, Any, Tuple
import logging

from ..models import CurriculumPlan, SourceCitation

logger = logging.getLogger(__name__)


def validate_curriculum(curriculum: CurriculumPlan) -> Dict[str, Any]:
    """
    Comprehensive validation of a curriculum plan.
    
    Args:
        curriculum: Curriculum plan to validate
        
    Returns:
        Validation results with errors, warnings, and scores
    """
    
    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'scores': {},
        'suggestions': []
    }
    
    # Basic structure validation
    _validate_basic_structure(curriculum, results)
    
    # Time allocation validation
    _validate_time_allocation(curriculum, results)
    
    # Source validation
    _validate_sources(curriculum, results)
    
    # Content quality validation
    _validate_content_quality(curriculum, results)
    
    # Learning progression validation
    _validate_learning_progression(curriculum, results)
    
    # Set overall validity
    results['valid'] = len(results['errors']) == 0
    
    return results


def validate_sources(sources: List[SourceCitation]) -> Dict[str, Any]:
    """
    Validate source citations for quality and completeness.
    
    Args:
        sources: List of source citations
        
    Returns:
        Validation results
    """
    
    results = {
        'valid': True,
        'errors': [],
        'warnings': [],
        'stats': {}
    }
    
    if not sources:
        results['errors'].append("No sources provided")
        results['valid'] = False
        return results
    
    # Check for duplicates
    source_ids = [source.source_id for source in sources]
    if len(source_ids) != len(set(source_ids)):
        results['warnings'].append("Duplicate source IDs found")
    
    # Validate individual sources
    valid_sources = 0
    for source in sources:
        if _is_valid_source(source):
            valid_sources += 1
        else:
            results['warnings'].append(f"Source '{source.title}' missing key information")
    
    # Check source diversity
    document_types = [source.document_type for source in sources if source.document_type]
    type_diversity = len(set(document_types)) / max(len(document_types), 1)
    
    if type_diversity < 0.3:
        results['warnings'].append("Low source type diversity")
    
    # Calculate stats
    results['stats'] = {
        'total_sources': len(sources),
        'valid_sources': valid_sources,
        'completion_rate': valid_sources / len(sources),
        'type_diversity': type_diversity,
        'avg_relevance_score': sum(s.relevance_score for s in sources) / len(sources),
        'avg_confidence_score': sum(s.confidence_score for s in sources) / len(sources)
    }
    
    return results


def _validate_basic_structure(curriculum: CurriculumPlan, results: Dict[str, Any]) -> None:
    """Validate basic curriculum structure."""
    
    # Check week count
    if len(curriculum.weekly_modules) != 4:
        results['errors'].append(f"Expected 4 weeks, got {len(curriculum.weekly_modules)}")
    
    # Check week numbering
    week_numbers = [week.week_number for week in curriculum.weekly_modules]
    if sorted(week_numbers) != [1, 2, 3, 4]:
        results['errors'].append(f"Invalid week numbering: {week_numbers}")
    
    # Check each week has tasks
    for week in curriculum.weekly_modules:
        if not week.daily_tasks:
            results['errors'].append(f"Week {week.week_number} has no daily tasks")
            continue
        
        # Check daily task structure
        expected_days = {'monday', 'tuesday', 'wednesday', 'thursday', 'friday'}
        actual_days = set(week.daily_tasks.keys())
        
        if not actual_days.issubset(expected_days):
            invalid_days = actual_days - expected_days
            results['warnings'].append(f"Week {week.week_number} has invalid days: {invalid_days}")
        
        # Check each day has tasks
        for day, tasks in week.daily_tasks.items():
            if not tasks:
                results['warnings'].append(f"Week {week.week_number}, {day} has no tasks")


def _validate_time_allocation(curriculum: CurriculumPlan, results: Dict[str, Any]) -> None:
    """Validate time allocation across the curriculum."""
    
    total_hours = curriculum.calculate_total_hours()
    
    # Check total duration
    if total_hours < 60:
        results['errors'].append(f"Total duration too short: {total_hours:.1f} hours")
    elif total_hours > 250:
        results['errors'].append(f"Total duration too long: {total_hours:.1f} hours")
    elif total_hours < 80:
        results['warnings'].append(f"Total duration quite short: {total_hours:.1f} hours")
    elif total_hours > 200:
        results['warnings'].append(f"Total duration quite long: {total_hours:.1f} hours")
    
    # Check daily averages
    daily_hours = []
    for week in curriculum.weekly_modules:
        for day_tasks in week.daily_tasks.values():
            if day_tasks:
                day_minutes = sum(task.estimated_duration_minutes for task in day_tasks)
                daily_hours.append(day_minutes / 60.0)
    
    if daily_hours:
        avg_daily = sum(daily_hours) / len(daily_hours)
        max_daily = max(daily_hours)
        min_daily = min(daily_hours)
        
        if max_daily > 10:
            results['warnings'].append(f"Some days too long: {max_daily:.1f} hours")
        if min_daily < 2:
            results['warnings'].append(f"Some days too short: {min_daily:.1f} hours")
        if avg_daily > 8:
            results['warnings'].append(f"Average daily load high: {avg_daily:.1f} hours")
        
        results['scores']['time_distribution'] = _calculate_time_distribution_score(daily_hours)


def _validate_sources(curriculum: CurriculumPlan, results: Dict[str, Any]) -> None:
    """Validate source citations in the curriculum."""
    
    all_sources = curriculum.get_all_sources()
    
    if not all_sources:
        results['errors'].append("No source citations found")
        return
    
    if len(all_sources) < 5:
        results['warnings'].append(f"Few sources cited: {len(all_sources)}")
    
    # Check source distribution across weeks
    source_counts_by_week = []
    for week in curriculum.weekly_modules:
        week_sources = set()
        for day_tasks in week.daily_tasks.values():
            for task in day_tasks:
                for source in task.sources:
                    week_sources.add(source.source_id)
        source_counts_by_week.append(len(week_sources))
    
    if any(count == 0 for count in source_counts_by_week):
        results['warnings'].append("Some weeks have no source citations")
    
    # Validate source quality
    source_validation = validate_sources(all_sources)
    if not source_validation['valid']:
        results['warnings'].extend(source_validation['warnings'])
    
    results['scores']['source_quality'] = source_validation['stats']['completion_rate']


def _validate_content_quality(curriculum: CurriculumPlan, results: Dict[str, Any]) -> None:
    """Validate content quality and completeness."""
    
    # Check for task diversity
    all_task_types = []
    for week in curriculum.weekly_modules:
        for day_tasks in week.daily_tasks.values():
            for task in day_tasks:
                all_task_types.append(task.task_type)
    
    unique_types = set(all_task_types)
    type_diversity = len(unique_types) / 6  # 6 possible task types
    
    if type_diversity < 0.5:
        results['warnings'].append("Low task type diversity")
    
    results['scores']['task_diversity'] = type_diversity
    
    # Check for learning objectives
    tasks_with_objectives = 0
    total_tasks = 0
    
    for week in curriculum.weekly_modules:
        for day_tasks in week.daily_tasks.values():
            for task in day_tasks:
                total_tasks += 1
                if task.learning_objectives:
                    tasks_with_objectives += 1
    
    if total_tasks > 0:
        objective_coverage = tasks_with_objectives / total_tasks
        if objective_coverage < 0.7:
            results['warnings'].append("Many tasks lack learning objectives")
        results['scores']['objective_coverage'] = objective_coverage
    
    # Check for assessments
    has_assessments = any(
        any(
            any(task.task_type.value == 'assessment' for task in day_tasks)
            for day_tasks in week.daily_tasks.values()
        )
        for week in curriculum.weekly_modules
    )
    
    if not has_assessments:
        results['warnings'].append("No assessment tasks found")


def _validate_learning_progression(curriculum: CurriculumPlan, results: Dict[str, Any]) -> None:
    """Validate logical learning progression."""
    
    # Check week progression
    week_complexities = []
    
    for week in curriculum.weekly_modules:
        complexity_score = 0
        task_count = 0
        
        for day_tasks in week.daily_tasks.values():
            for task in day_tasks:
                task_count += 1
                
                # Simple complexity scoring
                if task.task_type.value in ['training', 'hands_on']:
                    complexity_score += 2
                elif task.task_type.value in ['reading', 'meeting']:
                    complexity_score += 1
                elif task.task_type.value == 'assessment':
                    complexity_score += 3
        
        if task_count > 0:
            week_complexities.append(complexity_score / task_count)
    
    # Check for reasonable progression (allowing for some variation)
    if len(week_complexities) >= 3:
        if week_complexities[0] > week_complexities[-1]:
            results['suggestions'].append("Consider increasing complexity over time")
        
        # Check for extreme jumps
        for i in range(1, len(week_complexities)):
            jump = week_complexities[i] - week_complexities[i-1]
            if jump > 1.5:
                results['warnings'].append(f"Large complexity jump in week {i+1}")


def _calculate_time_distribution_score(daily_hours: List[float]) -> float:
    """Calculate score for time distribution quality."""
    
    if not daily_hours:
        return 0.0
    
    avg_hours = sum(daily_hours) / len(daily_hours)
    
    # Ideal range is 6-8 hours per day
    if 6 <= avg_hours <= 8:
        base_score = 1.0
    elif 4 <= avg_hours <= 10:
        base_score = 0.8
    else:
        base_score = 0.5
    
    # Penalize high variance
    variance = sum((h - avg_hours) ** 2 for h in daily_hours) / len(daily_hours)
    std_dev = variance ** 0.5
    
    if std_dev > 3:  # High variance
        base_score *= 0.7
    elif std_dev > 2:
        base_score *= 0.9
    
    return base_score


def _is_valid_source(source: SourceCitation) -> bool:
    """Check if a source citation has sufficient information."""
    
    required_fields = [source.source_id, source.title, source.document_type]
    if not all(required_fields):
        return False
    
    # Should have either URL or file path
    if not (source.url or source.file_path):
        return False
    
    return True