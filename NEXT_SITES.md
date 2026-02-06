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

### 📋 ALREADY COVERED (no separate scraper needed)

5. **City of Sacramento** — ✅ Covered by **GovernmentJobs.com** scraper (searches by zip 95826 + keywords).
6. **County of Sacramento** — ✅ Covered by **GovernmentJobs.com** scraper.
7. **CalPERS** — ✅ Covered by **State of California (CalCareers)** scraper; CalPERS posts on CalCareers.

### 🔜 NEXT TO ADD (own career sites, not yet scraped)

8. **Golden 1 Credit Union** (`golden1`) ✅ DONE
   - **URL**: https://jobs.dayforcehcm.com/en-US/golden1/CANDIDATEPORTAL
   - **Platform**: Dayforce HCM (Next.js + JSON API)
   - **Why**: Sacramento HQ, IT/security roles (e.g. Business Systems Analyst, Help Desk).
   - **Features**:
     - Browser session for Cloudflare/CSRF token
     - JSON API for job listings with full descriptions included
     - Pagination via `?page=1`, `?page=2`, etc.
     - No separate description fetch needed (descriptions in listing response)
   - **Config**: Set `GOLDEN1_MAX_PAGES` in config.py (default: 15)

9. **VSP Global** (`vsp`) — **Next highest priority**
   - **URL**: Find their primary careers portal (e.g. careers.vspglobal.com or similar); also on aggregators.
   - **Why**: Rancho Cordova, large employer, IT/digital roles.
   - **Difficulty**: Medium (need to confirm platform).

10. **Sacramento State (CSUS)** (`csus`)
    - **URL**: https://www.csus.edu/administration-business-affairs/human-resources/careers/ (or CSU-wide system).
    - **Why**: Local university IT, may use different system than UC Davis.
    - **Difficulty**: Medium (check if CSU-wide job board or separate).

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
