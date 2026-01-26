# AI Job Hunter 🎯

![AI Job Hunter Banner](assets/ai-job-hungter.png)

An AI-powered job search automation tool that scrapes job listings, filters them based on your preferences, and uses AI to score how well each job matches your background.

## Features

- **Multi-site scraping**: Search multiple job boards (PG&E, SMUD, Kaiser Permanente, State of California)
- **Smart filtering**: Automatically filters out senior/expert roles and irrelevant clinical/medical fields
- **AI-powered Title Pre-Filtering**: Uses AI to scan hundreds of job titles and identify the relevant ones before fetching full descriptions
- **AI-powered matching**: Uses Groq AI to score jobs 1-10 based on YOUR specific background
- **Excel export**: Generates a master Excel file with clickable apply links and source-specific tabs
- **Deduplication**: Tracks jobs in a local database so you never see duplicates
- **Anti-Bot Protection**: Built-in delays and human-like behavior to prevent IP blocks

## Quick Start

### 1. Clone the repo
```bash
git clone https://github.com/YOUR_USERNAME/ai-job-hunter.git
cd ai-job-hunter
```

### 2. Set up Python environment
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 3. Configure your profile
```bash
# Copy the template
cp config_template.py config.py

# Edit config.py with your background, skills, and target roles
nano config.py  # or use your preferred editor
```

### 4. Set up your API key
```bash
# Copy the example env file
cp .env.example .env

# Add your Groq API key (free at https://console.groq.com)
nano .env
```

### 5. Run the job hunter
```bash
python3 main.py
```

## Output

After running, you'll have:
- **`jobs_master.xlsx`**: Excel file with all jobs, sorted by match score
- **`jobs.db`**: SQLite database tracking all jobs (for deduplication)

### Priority Guide
| Score | Priority | Action |
|-------|----------|--------|
| 8-10 | ⭐ HIGH | Apply ASAP! |
| 5-7 | ✅ MEDIUM | Worth applying |
| 1-4 | 📋 LOW | Only if desperate |

## Configuration

### `config.py`

| Variable | Description |
|----------|-------------|
| `YOUR_BACKGROUND` | Your education, skills, projects, and target roles |
| `SEARCH_QUERIES` | Keywords to search for on PG&E/SMUD |
| `KAISER_LOCATION_URL` | The specific location search URL for Kaiser Permanente |
| `STATE_CA_LOCATION` | Location name for State CA ("Sacramento County", "Los Angeles County", None=all) |
| `STATE_CA_KEYWORDS` | Keywords to search on CalCareers (e.g., IT, Security, Analyst) |
| `ENTRY_LEVEL_INDICATORS` | Words that mark a job as entry-level (always kept) |
| `NOISE_KEYWORDS` | Words that filter out senior roles |
| `IGNORE_FIELDS` | Massive list of keywords to ignore (e.g., Clinical, Medical) |
| `INTEREST_KEYWORDS` | Priority keywords for your tech background (used for AI scanning) |
| `ENABLED_SITES` | Toggle which job sites to search |

### `.env`

```
GROQ_API_KEY=your_api_key_here
```

Get a free API key at [console.groq.com](https://console.groq.com)

## Supported Job Sites

| Site | Status | Notes |
|------|--------|-------|
| PG&E | ✅ Working | Pacific Gas & Electric |
| SMUD | ✅ Working | Sacramento Municipal Utility District |
| Kaiser | ✅ Working | Kaiser Permanente (Full Location Scrape) |
| State CA | ✅ Working | State of California (CalCareers) - configurable county |

## Commands

```bash
# Run full job search + AI analysis
python3 main.py

# Export current database to Excel (without re-scraping)
python3 export_excel.py
```

## How It Works

1. **Scrape**: Uses Playwright to search job sites for your keywords (or full location dump)
2. **Filter**: Removes senior/expert roles and clinical fields via keyword matching
3. **AI Pre-Filter**: Groq AI scans all remaining titles to pick the most relevant technical roles
4. **Dedupe**: Checks against database to find only NEW jobs
5. **Fetch**: Gets full job descriptions for new jobs (with 10s delays for bot safety)
6. **Analyze**: Groq AI performs a deep analysis of the job description vs your profile
7. **Export**: Creates/updates master Excel file with clickable links

## License

MIT License - Use it, modify it, land that job! 🚀

## Disclaimer

This tool is for personal job searching only. Be respectful of job site rate limits and terms of service. The AI scores are suggestions, not guarantees - always read the full job description before applying.
