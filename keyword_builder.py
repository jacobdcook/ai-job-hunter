"""
Keyword Builder - Generates expanded SOC-adjacent keyword groups for searching.
Used by SOC Feeder Mode to search beyond generic IT keywords.
"""

from taxonomy import SOC_DIRECT_KEYWORDS, SOC_ADJACENT, IT_FEEDER_KEYWORDS, INTERNSHIP_KEYWORDS


def build_soc_keywords_for_site(site_name: str, config, include_internships: bool = True) -> list:
    """
    Build expanded keyword list for a specific site, including SOC-adjacent terms.

    Args:
        site_name: Site key (e.g., 'state_ca', 'pge', 'sutter')
        config: Config module with keyword settings
        include_internships: Include internship/apprenticeship keywords

    Returns:
        List of keywords to search (respects per-site limits)
    """
    keywords = []

    # Add SOC_DIRECT keywords (top priority)
    keywords.extend(SOC_DIRECT_KEYWORDS)

    # Add high-value SOC_ADJACENT categories based on priority order
    if hasattr(config, 'SOC_FEEDER_SEARCH_PRIORITY'):
        for category in config.SOC_FEEDER_SEARCH_PRIORITY:
            if category in SOC_ADJACENT:
                keywords.extend(SOC_ADJACENT[category]['keywords'])

    # Add IT_FEEDER keywords
    keywords.extend(IT_FEEDER_KEYWORDS[:5])  # Top 5 to avoid bloat

    # Add internship keywords if requested
    if include_internships:
        keywords.extend(INTERNSHIP_KEYWORDS[:8])  # Common ones: intern, internship, apprentice, trainee, rotation, etc.

    # Apply site-specific overrides if configured
    if hasattr(config, 'SITE_KEYWORD_OVERRIDES') and site_name in config.SITE_KEYWORD_OVERRIDES:
        site_overrides = config.SITE_KEYWORD_OVERRIDES[site_name]
        if 'exclude_categories' in site_overrides:
            # Remove keywords from excluded categories
            exclude_cats = site_overrides['exclude_categories']
            for cat in exclude_cats:
                if cat in SOC_ADJACENT:
                    for kw in SOC_ADJACENT[cat]['keywords']:
                        keywords = [k for k in keywords if k != kw]

    # Remove duplicates while preserving order
    seen = set()
    unique_keywords = []
    for kw in keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            unique_keywords.append(kw)

    # Apply per-site keyword limit (default 15)
    keyword_limit = getattr(config, 'SOC_FEEDER_KEYWORDS_PER_SITE', 15)
    return unique_keywords[:keyword_limit]


def merge_with_existing_keywords(soc_keywords: list, existing_keywords: list) -> list:
    """
    Merge SOC keywords with existing site keywords, avoiding duplicates.

    Args:
        soc_keywords: SOC-adjacent expanded keywords
        existing_keywords: Site's existing keyword list

    Returns:
        Combined keyword list
    """
    seen = set()
    merged = []

    # SOC keywords first (higher priority)
    for kw in soc_keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            merged.append(kw)

    # Then existing keywords
    for kw in existing_keywords:
        if kw.lower() not in seen:
            seen.add(kw.lower())
            merged.append(kw)

    return merged


def get_keywords_for_site(site_name: str, config) -> list:
    """
    Get keywords for a specific site, using SOC expansion if enabled.

    Args:
        site_name: Site key
        config: Config module

    Returns:
        List of keywords to use for scraping
    """
    # If SOC Feeder Mode is not enabled, use site defaults
    if not getattr(config, 'ENABLE_SOC_FEEDER_MODE', False):
        return get_default_keywords_for_site(site_name, config)

    # Build expanded SOC keywords
    soc_keywords = build_soc_keywords_for_site(site_name, config)

    # Merge with existing site keywords
    existing = get_default_keywords_for_site(site_name, config)
    return merge_with_existing_keywords(soc_keywords, existing)


def get_default_keywords_for_site(site_name: str, config) -> list:
    """
    Get default keywords for a site from config.

    Args:
        site_name: Site key
        config: Config module

    Returns:
        Default keyword list for the site
    """
    keyword_map = {
        'pge': lambda: getattr(config, 'SEARCH_QUERIES', []),
        'smud': lambda: getattr(config, 'SEARCH_QUERIES', []),
        'state_ca': lambda: getattr(config, 'STATE_CA_KEYWORDS', []),
        'ucdavis': lambda: getattr(config, 'UCDAVIS_KEYWORDS', []),
        'sutter': lambda: getattr(config, 'SUTTER_KEYWORDS', []),
        'government_jobs': lambda: getattr(config, 'GOVERNMENT_JOBS_KEYWORDS', []),
        'blueshield': lambda: getattr(config, 'BLUESHIELD_KEYWORDS', []),
        'losrios': lambda: getattr(config, 'LOSRIOS_KEYWORDS', []),
    }

    if site_name in keyword_map:
        return keyword_map[site_name]()
    return []
