"""
Job site scrapers module.
Each scraper follows a common interface for easy integration.
"""

from .pge import scrape_pge_jobs, fetch_pge_descriptions_batch
from .smud import scrape_smud_jobs, fetch_smud_descriptions_batch, scrape_all_smud_jobs
from .kaiser import scrape_kaiser_jobs, fetch_kaiser_descriptions_batch, scrape_all_kaiser_jobs
from .state_ca import scrape_state_ca_jobs, fetch_state_ca_descriptions_batch, scrape_all_state_ca_jobs

__all__ = [
    'scrape_pge_jobs', 'fetch_pge_descriptions_batch',
    'scrape_smud_jobs', 'fetch_smud_descriptions_batch', 'scrape_all_smud_jobs',
    'scrape_kaiser_jobs', 'fetch_kaiser_descriptions_batch', 'scrape_all_kaiser_jobs',
    'scrape_state_ca_jobs', 'fetch_state_ca_descriptions_batch', 'scrape_all_state_ca_jobs',
]
