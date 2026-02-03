# Next Job Sites to Add

## Priority Order (Based on Job Volume + Your Background)

### 🔥 HIGH PRIORITY

1. **State of California** (`state_ca`) ✅ DONE
   - **URL**: https://www.calcareers.ca.gov/
   - **Why**: Largest employer in CA, TONS of IT/Security roles
   - **Search**: Configurable keywords (default: IT, Security, Analyst, Systems, Network, Cyber)
   - **Location**: Configurable by location ID (default: 418 = Sacramento County)
   - **Features**: 
     - URL-based search with `#kw=keyword&locid=xxx`
     - ASP.NET pagination handling (clicks "Next" button)
     - 10+ second delays between requests to avoid blocking
     - IP block detection with auto-stop
   - **Config**: Set `STATE_CA_LOCATION_ID` and `STATE_CA_KEYWORDS` in config.py

2. **Kaiser Permanente** (`kaiser`) ✅ DONE
   - **URL**: https://www.kaiserpermanentejobs.org/
   - **Status**: Fully implemented with AI pre-filtering and bot protection
   - **Features**: Full location scrape, 10-second delays, IP block detection

3. **UC Davis** (`ucdavis`) ⚠️ IMPLEMENTED — CLOUDFLARE BLOCK
   - **URL**: https://hr.ucdavis.edu/careers/apply
   - **Why**: University IT/security, Davis location, good benefits
   - **Search**: Configurable keywords (default: IT, Security, Analyst, Associate)
   - **Location**: Davis, Sacramento, Remote (all locations)
   - **Features**: 
     - Keyword-based search via URL params
     - Pagination handling (clicks "Next" button)
     - 10+ second delays between requests
   - **Config**: Set `UCDAVIS_KEYWORDS` in config.py
   - **Limitation**: UC Davis uses **Cloudflare** and often blocks automated/headless requests. Run with **browser visible** (`headless=False`) from your own machine; if you still get 0 jobs, the IP may be blocked. Use "UC Davis only" (option 5) to test.

4. **Sutter Health** (`sutter`) ✅ DONE
   - **URL**: https://jobs.sutterhealth.org/
   - **Why**: Healthcare IT/security, Sacramento area
   - **Platform**: Phenom People (server-side rendered)
   - **Search**: Configurable keywords (default: IT, Security, Analyst, Help Desk)
   - **Features**:
     - Pure HTTP (aiohttp) -- no browser needed
     - Job data embedded in HTML as `phApp.ddo` JSON
     - Pagination via `?keywords={kw}&from={offset}&s=1` (10 per page, fixed)
     - Full descriptions from detail pages via `phApp.ddo.jobDetail.data.job.description`
     - 2-3 second delays between requests
   - **Config**: Set `SUTTER_KEYWORDS` in config.py

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
