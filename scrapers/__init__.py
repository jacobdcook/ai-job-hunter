"""
Job site scrapers module.
Each scraper follows a common interface for easy integration.
"""

from .pge import scrape_pge_jobs, fetch_pge_descriptions_batch
from .smud import scrape_smud_jobs, fetch_smud_descriptions_batch, scrape_all_smud_jobs
from .kaiser import scrape_kaiser_jobs, fetch_kaiser_descriptions_batch, scrape_all_kaiser_jobs
from .state_ca import scrape_state_ca_jobs, fetch_state_ca_descriptions_batch, scrape_all_state_ca_jobs
from .ucdavis import scrape_ucdavis_jobs, fetch_ucdavis_descriptions_batch
from .sutter import scrape_sutter_jobs, fetch_sutter_descriptions_batch
from .commonspirit import scrape_commonspirit_jobs, fetch_commonspirit_descriptions_batch
from .government_jobs import scrape_government_jobs, fetch_job_details
from .intel import scrape_intel_jobs, fetch_intel_descriptions_batch
from .blueshield import scrape_blueshield_jobs, fetch_blueshield_descriptions_batch
from .losrios import scrape_losrios_jobs, fetch_losrios_descriptions_batch
from .golden1 import scrape_golden1_jobs, fetch_golden1_descriptions_batch

__all__ = [
    'scrape_pge_jobs', 'fetch_pge_descriptions_batch',
    'scrape_smud_jobs', 'fetch_smud_descriptions_batch', 'scrape_all_smud_jobs',
    'scrape_kaiser_jobs', 'fetch_kaiser_descriptions_batch', 'scrape_all_kaiser_jobs',
    'scrape_state_ca_jobs', 'fetch_state_ca_descriptions_batch', 'scrape_all_state_ca_jobs',
    'scrape_ucdavis_jobs', 'fetch_ucdavis_descriptions_batch',
    'scrape_sutter_jobs', 'fetch_sutter_descriptions_batch',
    'scrape_commonspirit_jobs', 'fetch_commonspirit_descriptions_batch',
    'scrape_government_jobs', 'fetch_job_details',
    'scrape_intel_jobs', 'fetch_intel_descriptions_batch',
    'scrape_blueshield_jobs', 'fetch_blueshield_descriptions_batch',
    'scrape_losrios_jobs', 'fetch_losrios_descriptions_batch',
    'scrape_golden1_jobs', 'fetch_golden1_descriptions_batch',
]
