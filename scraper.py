"""
DEPRECATED: This file is kept for backwards compatibility.
The scrapers have been moved to the 'scrapers/' folder.

Use:
    from scrapers.pge import scrape_pge_jobs, fetch_pge_descriptions_batch
    from scrapers.smud import scrape_smud_jobs, fetch_smud_descriptions_batch
"""

# Re-export for backwards compatibility
from scrapers.pge import scrape_pge_jobs, fetch_pge_descriptions_batch
from scrapers.pge import scrape_pge_jobs as scrape_pge_jobs
from config import NOISE_KEYWORDS, ENTRY_LEVEL_INDICATORS


def filter_jobs(jobs):
    """
    Filters out senior/expert/principal roles unless they're explicitly entry-level.
    """
    filtered_jobs = []
    
    for job in jobs:
        title = job["title"]
        title_lower = title.lower()
        
        is_entry_level = any(indicator.lower() in title_lower for indicator in ENTRY_LEVEL_INDICATORS)
        has_noise = any(keyword.lower() in title_lower for keyword in NOISE_KEYWORDS)
        
        if is_entry_level or not has_noise:
            filtered_jobs.append(job)
    
    return filtered_jobs


# Alias for backwards compatibility
fetch_descriptions_batch = fetch_pge_descriptions_batch
