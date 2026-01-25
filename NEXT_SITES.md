# Next Job Sites to Add

## Priority Order (Based on Job Volume + Your Background)

### 🔥 HIGH PRIORITY

1. **State of California** (`state_ca`)
   - **URL**: https://www.calcareers.ca.gov/
   - **Why**: Largest employer in CA, TONS of IT/Security roles
   - **Search**: "Information Technology", "Security", "Analyst", "Associate"
   - **Location**: Sacramento (many state jobs), Remote options
   - **Difficulty**: Medium (state job portal, might need to handle pagination)

2. **Kaiser Permanente** (`kaiser`)
   - **URL**: https://www.kaiserpermanentejobs.org/
   - **Why**: Healthcare IT/security is hot, big Sacramento presence
   - **Search**: "IT", "Security", "Analyst", "Associate", "Entry"
   - **Location**: Sacramento, Remote
   - **Difficulty**: Medium (likely uses standard ATS)

3. **UC Davis** (`ucdavis`)
   - **URL**: https://careers.ucdavis.edu/
   - **Why**: University IT/security, Davis location, good benefits
   - **Search**: "IT", "Security", "Analyst", "Associate"
   - **Location**: Davis, Sacramento, Remote
   - **Difficulty**: Medium (university job portal)

4. **Sutter Health** (`sutter`)
   - **URL**: https://www.sutterhealth.org/about/careers
   - **Why**: Healthcare IT/security, Sacramento area
   - **Search**: "IT", "Security", "Analyst"
   - **Location**: Sacramento, Remote
   - **Difficulty**: Medium

### 📋 MEDIUM PRIORITY

5. **City of Sacramento** (`city_sac`)
   - **URL**: https://www.governmentjobs.com/careers/sacramento
   - **Why**: Local government IT roles
   - **Difficulty**: Easy (uses governmentjobs.com - common platform)

6. **County of Sacramento** (`county_sac`)
   - **URL**: https://www.governmentjobs.com/careers/saccounty
   - **Why**: County IT/security roles
   - **Difficulty**: Easy (same platform as City)

7. **CalPERS** (`calpers`)
   - **URL**: https://www.calpers.ca.gov/page/careers
   - **Why**: Pension fund, IT/security roles
   - **Difficulty**: Medium

## Search Strategy

### Current Keywords (Keep These):
- Security, Cyber, Associate, Trainee, Apprentice
- IT Analyst, Systems Analyst, Infrastructure, Compliance
- Network, Support, Technician, Operations Analyst
- Intern, Internship

### Location Filters to Add:
- Sacramento, CA
- Davis, CA  
- Remote
- California (for state jobs)

### Additional Keywords to Consider:
- "SOC" (Security Operations Center)
- "Incident Response"
- "SIEM"
- "Compliance Analyst"
- "IT Support"
- "Help Desk" (foot-in-door)

## Implementation Notes

Each scraper should:
1. Search by keyword (like PG&E)
2. Filter by location if possible (Sacramento, Davis, Remote)
3. Extract: title, link, location, date_posted, source
4. Follow the same interface as `pge.py` and `smud.py`

## Quick Start

To add a new site:
1. Create `scrapers/[site_name].py`
2. Implement `scrape_[site]_jobs(query, headless=False)` 
3. Implement `fetch_[site]_descriptions_batch(jobs, headless=False)`
4. Add to `ENABLED_SITES` in `config.py`
5. Update `main.py` to call it
6. Update `select_sites()` menu
