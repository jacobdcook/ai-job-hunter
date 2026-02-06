"""
Job Classifier - Integrates taxonomy-based SOC feeder classification with Groq scoring.
Classifies jobs and calculates combined priority scores.
"""

from taxonomy import classify_job, calculate_priority_score
from database import generate_job_id, update_job_feeder_classification
import sqlite3

DB_NAME = "jobs.db"


def classify_and_score_job(title: str, description: str = "", groq_score: int = None) -> dict:
    """
    Classify a job using taxonomy and optionally combine with Groq score.

    Args:
        title: Job title
        description: Job description
        groq_score: AI score from Groq (1-10) - if None, uses taxonomy score only

    Returns:
        {
            'category': str,
            'subcategory': str,
            'feeder_score': int (0-100),
            'reasons': list,
            'is_internship': bool,
            'is_shift_based': bool,
            'priority_score': float (0-100),
            'matched_keywords': list
        }
    """
    # Get taxonomy classification
    classification = classify_job(title, description)

    # Calculate priority score combining Groq + taxonomy
    if groq_score is not None:
        priority_score = calculate_priority_score(
            groq_score,
            classification['feeder_score'],
            classification['is_internship'],
            classification['is_shift_based']
        )
    else:
        # Without Groq score, use feeder score as base
        priority_score = classification['feeder_score']
        if classification['is_internship']:
            priority_score += 10
        if classification['is_shift_based']:
            priority_score += 8

    classification['priority_score'] = min(100, priority_score)

    return classification


def apply_classification_to_database(job_id: str, title: str, description: str = ""):
    """
    Classify a job in the database and update its feeder fields.

    Args:
        job_id: Job ID in database
        title: Job title
        description: Job description
    """
    classification = classify_job(title, description)

    # Format reasons as comma-separated string
    reasons_str = " | ".join(classification['reasons']) if classification['reasons'] else ""

    update_job_feeder_classification(
        job_id,
        classification['category'],
        classification['feeder_score'],
        reasons_str,
        0  # priority_score will be set when Groq score is available
    )


def should_skip_job_by_category(category: str, config) -> bool:
    """
    Determine if a job should be skipped based on its category and config.

    Args:
        category: Job category (SOC_DIRECT, SOC_ADJACENT, IT_FEEDER, AVOID)
        config: Config module with MIN_FEEDER_SCORE_TO_KEEP

    Returns:
        True if job should be skipped, False otherwise
    """
    if config.ENABLE_SOC_FEEDER_MODE:
        if category == 'AVOID':
            return True
        # Category maps to scores:
        # SOC_DIRECT = 100, SOC_ADJACENT = 60-95, IT_FEEDER = 50, AVOID = 0
        category_to_min_score = {
            'SOC_DIRECT': 100,
            'SOC_ADJACENT': 60,
            'IT_FEEDER': 50,
            'AVOID': -1  # Always skip
        }
        min_score_for_category = category_to_min_score.get(category, 0)
        return min_score_for_category < config.MIN_FEEDER_SCORE_TO_KEEP
    return False


def format_category_for_excel(category: str, feeder_score: int) -> str:
    """
    Format category for Excel display with emoji indicators.

    Args:
        category: Job category
        feeder_score: Feeder score (0-100)

    Returns:
        Formatted string for Excel
    """
    icons = {
        'SOC_DIRECT': '🎯',
        'SOC_ADJACENT': '⬆️',
        'IT_FEEDER': '📚',
        'AVOID': '❌'
    }
    icon = icons.get(category, '❓')
    return f"{icon} {category} ({feeder_score})"
