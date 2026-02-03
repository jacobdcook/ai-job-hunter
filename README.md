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

### 2. Set up Python environment & install dependencies
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

⚠️ **IMPORTANT: Keep the venv activated!** Every time you open a new terminal, run:
```bash
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Run the setup wizard (Auto-generates config.py)
```bash
# Make sure venv is activated (see step 2)
python main.py

# On first run, you'll see a setup wizard prompt
# Select option 0) SETUP WIZARD
# Answer the friendly questions about your background and preferences
# The wizard will auto-generate config.py for you!
# Supports pasting resume/profile text for better AI matching
```

**No manual config editing needed!** The setup wizard handles everything.

**Option B: Manual Configuration**
```bash
# Copy the template
cp config_template.py config.py

# Edit config.py with your background, skills, and target roles
nano config.py  # or use your preferred editor
```

### 4. Add your Groq API key
```bash
cp .env.example .env
nano .env  # Add your free Groq API key from https://console.groq.com
```

### 5. Run the job hunter
```bash
python main.py
# Select your options (scrape, analyze, export)
# Results saved to: jobs_master.xlsx
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

### `config.py` - Key Settings to Customize

**Start with these (modify for your situation):**

| Variable | Purpose | Example |
|----------|---------|---------|
| `YOUR_BACKGROUND` | ⭐ **YOUR PROFILE** - Describe your skills, experience, target roles | "5 years Python, Azure security, Linux" |
| `SEARCH_QUERIES` | Keywords to search (PG&E, SMUD, etc.) | `["IT", "Security", "Network"]` |
| `INTEREST_KEYWORDS` | High-priority tech terms your background matches | `["Cyber", "Security", "Python", "Cloud"]` |
| `NOISE_KEYWORDS` | Filter out senior/mgmt roles you don't want | `["Senior", "Manager", "Director"]` |
| `IGNORE_FIELDS` | **AVOID THESE** - Clinical, medical, non-tech roles | `["Nurse", "RN", "Doctor"]` - 150+ pre-configured |

**Advanced settings (location-specific):**

| Variable | Purpose | Example |
|----------|---------|---------|
| `STATE_CA_LOCATION` | CA state jobs: filter by county | `"Sacramento County"` or `None` for all |
| `STATE_CA_KEYWORDS` | CA state search keywords | `["IT", "Analyst", "Systems"]` |
| `KAISER_LOCATION_URL` | Kaiser: change location search URL | Modify the URL with your target county |
| `ENABLED_SITES` | Toggle which job sites to search | Set to `True`/`False` |
| `ENTRY_LEVEL_INDICATORS` | Mark jobs as entry-level to keep | `["Junior", "Intern", "Entry"]` |

### `.env` - API Keys

```
GROQ_API_KEY=your_api_key_here
```

**Get a free Groq API key:**
1. Go to [console.groq.com](https://console.groq.com)
2. Sign up for free
3. Create an API key
4. Add it to your `.env` file

### Customization Quick Guide

**Fastest setup (2-3 minutes with Setup Wizard):**
```bash
python3 main.py
# Select: 0) SETUP WIZARD
# Answer friendly prompts about your background, skills, and job preferences
# Wizard generates config.py automatically!
# (Optional: Paste your resume for better AI matching)
```

**That's it!** After setup, the tool will:
- ✅ Scrape multiple job sites based on your preferences
- ✅ Filter out irrelevant roles automatically
- ✅ Use AI to score each job's match to your background
- ✅ Save results to `jobs_master.xlsx` with clickable apply links

## Supported Job Sites

| Site | Status | Notes |
|------|--------|-------|
| PG&E | ✅ Working | Pacific Gas & Electric |
| SMUD | ✅ Working | Sacramento Municipal Utility District |
| Kaiser | ✅ Working | Kaiser Permanente (Full Location Scrape) |
| State CA | ✅ Working | State of California (CalCareers) - configurable county |
| CommonSpirit | ✅ Working | CommonSpirit Health (Dignity Health, CHI, Virginia Mason) |
| Sutter Health | ✅ Working | Sutter Health hospitals |
| UC Davis | ✅ Working | UC Davis Health & administration |

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
