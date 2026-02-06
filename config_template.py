"""
Configuration Template for AI Job Hunter

INSTRUCTIONS:
1. Copy this file and rename it to 'config.py'
2. Fill in YOUR_BACKGROUND with your own info
3. Customize SEARCH_QUERIES for the types of jobs you want
4. Adjust FILTERS (ENTRY_LEVEL_INDICATORS, NOISE_KEYWORDS, IGNORE_FIELDS)
5. Set INTEREST_KEYWORDS for the AI pre-filter
"""

YOUR_BACKGROUND = """
- Name: [Your Name]
- Education: [Your Degree(s) and School(s)]
- Certifications: [Any certs you have - e.g., CompTIA Security+, AWS, etc.]
- Core Skills: [List your top technical skills]
- Key Projects: 
  * [Project 1]: Brief description
  * [Project 2]: Brief description
- Work History: [Brief summary of relevant work experience]
- Target Roles: [Types of jobs you're looking for]
"""

# =============================================================================
# JOB SITES CONFIGURATION
# =============================================================================
# Enable/disable which job sites to search
ENABLED_SITES = {
    "pge": True,           # Pacific Gas & Electric
    "smud": True,          # Sacramento Municipal Utility District
    "kaiser": True,        # Kaiser Permanente
    "state_ca": True,      # State of California (CalCareers)
    "ucdavis": True,       # UC Davis
    "sutter": True,        # Sutter Health
    "commonspirit": True,  # CommonSpirit Health (Dignity Health, CHI)
    "government_jobs": True,  # GovernmentJobs.com (Government IT/Security roles)
    "intel": True,         # Intel Corporation (Folsom campus + Sacramento area)
}

# Kaiser Permanente specific URLs (Default: California, US)
# To change location: 
# 1. Go to https://www.kaiserpermanentejobs.org
# 2. Search for your location (e.g., "Texas, US")
# 3. Copy the URL path after the domain (e.g., "/search-jobs/Texas%2C%20US/...")
KAISER_LOCATION_URL = "/search-jobs/California%2C%20US/641/3/6252001-5332921/37x25022/-119x75126/25/2"
KAISER_KEYWORD_URL_TEMPLATE = "/search-jobs/{keyword}/California%2C%20US/641/1/3/6252001-5332921/37x25022/-119x75126/25/2"

# State of California (CalCareers) configuration
# Location options (use the exact county name as shown on the site):
#   "Sacramento County" - Default
#   "Los Angeles County"
#   "San Diego County"
#   None - Search all locations statewide
# Tip: Go to https://calcareers.ca.gov/CalHRPublic/Search/AdvancedJobSearch.aspx
#      and check the Location dropdown for exact county names
STATE_CA_LOCATION = "Sacramento County"

# Keywords to search on State CA jobs site (CalCareers)
# Searched separately; results combined and deduped by job link.
# CalCareers uses "Information Technology" and "Information" a lot for IT roles.
STATE_CA_KEYWORDS = [
    "Information Technology",  # CalCareers classification; catches many IT postings
    "Information",            # Broader match for IT/Info roles
    "IT",
    "Security",
    "Cyber",
    "Analyst",
    "Systems",
    "Network",
    "Technology",             # Catches "Information Technology" and similar
]

# UC Davis keywords
# Keywords to search on UC Davis careers site
UCDAVIS_KEYWORDS = ["IT", "Security", "Analyst", "Associate"]

# Sutter Health keywords
# Keywords to search on Sutter Health careers site
SUTTER_KEYWORDS = ["IT", "Security", "Analyst", "Help Desk", "Systems", "Network", "Cyber", "Infrastructure", "Support", "Technician"]

# CommonSpirit Health configuration (Dignity Health, CHI, Virginia Mason Franciscan Health)
# Website: https://www.commonspirit.careers
COMMONSPIRIT_ZIP = None  # Zip code for location search (e.g., "95826" for Sacramento). None searches default area.
COMMONSPIRIT_MAX_PAGES = 20  # Max pages to scrape (11 jobs per page, ~168 total jobs)

# GovernmentJobs.com configuration (Government IT & Security roles)
# Website: https://www.governmentjobs.com
# Optimized for IT security analyst, SOC analyst, and government tech roles
GOVERNMENT_JOBS_LOCATION = "95826"  # Zip code (default: Sacramento, CA)
GOVERNMENT_JOBS_DISTANCE = 100  # Search radius in miles
GOVERNMENT_JOBS_MAX_PAGES = 20  # Max pages to scrape (~20 jobs per page)
GOVERNMENT_JOBS_KEYWORDS = [
    "SOC Analyst",
    "Security Analyst",
    "Security Operations",
    "Threat Detection",
    "Incident Response",
    "IT Analyst",
    "Systems Admin",
    "Information Security",
    "Cybersecurity",
    "Network Security"
]

# Intel Corporation configuration
# Website: https://intel.wd1.myworkdayjobs.com/External
# Uses Workday API for job listings (no keyword search, just location filter)
INTEL_USE_LOCATION_FILTER = True  # True = Sacramento area (Folsom + nearby), False = All Intel jobs nationwide
INTEL_MAX_JOBS = 200  # Max jobs to scrape (default 200)

# =============================================================================
# PREFERRED CITIES (for "Near Me" Excel tab)
# =============================================================================
# Jobs with locations matching these cities get their own "Near Me" tab in Excel.
# This helps you prioritize local jobs while still seeing all jobs in the "All Jobs" tab.
# Case-insensitive substring match against the job's location field.
# Example: "Sacramento" matches "Sacramento, CA", "North Sacramento", etc.
#
# INSTRUCTIONS: Add the cities you live near or would commute to.
PREFERRED_CITIES = [
    # "Sacramento",
    # "San Francisco",
    # "Oakland",
    # "San Jose",
    # "Remote",
]

# =============================================================================
# SEARCH QUERIES
# =============================================================================
# These keywords will be used for searching job sites.
SEARCH_QUERIES = [
    "Security", "Cyber", "Associate", "Trainee", "Apprentice", 
    "Customer Service", "Representative", "RDP", "Rotation", "Rotational",
    "IT Analyst", "Systems Analyst", "Infrastructure", "Compliance",
    "Network", "Support", "Technician", "Operations Analyst",
    "Intern", "Internship"
]

# =============================================================================
# FILTERS (Noise & Entry-Level)
# =============================================================================

# Jobs with these words in the title are ALWAYS kept (overrides noise filter)
# Example: If you are looking for medical roles, you might add "Nurse" or "CNA" here.
ENTRY_LEVEL_INDICATORS = [
    "Associate", "Junior", "Entry", "Trainee", "Apprentice", 
    "Rotational", "Rotation", "RDP", "Representative", "Service", 
    "Clerk", "Support", "Technician", "Analyst I", "Level 1",
    "Intern", "Internship"
]

# Jobs with these words in the title are filtered OUT (unless they have an entry-level indicator)
# This is where you put "Senior", "Manager", etc.
NOISE_KEYWORDS = ["Senior", "Expert", "Principal", "Lead", "Chief", "Director", "Manager"]

# Hard seniority filter - ALWAYS filters these out even if title has interest keywords.
# Unlike NOISE_KEYWORDS (which are overridden by INTEREST_KEYWORDS), these are absolute.
SENIORITY_EXCLUDE = [
    "Senior", "Sr.", "Sr ", "Principal", "Lead", "Expert",
    "Director", "Manager", "Supervisor", "Chief", "VP",
    "Vice President", "Head of", "III", "IV", "V",
]

# Ignore these fields entirely (substring match, case-insensitive).
# INSTRUCTIONS: Add any keywords here that you want to IMMEDIATELY discard.
# If you are looking for medical jobs, REMOVE the medical keywords below.
IGNORE_FIELDS = [
    # =========================================================================
    # MEDICAL/CLINICAL - Core Roles & Terms
    # =========================================================================
    "Nurse", "Nursing", "Physician", "Medical", "Pharmacist", "Pharmacy",
    "Therapist", "Therapy", "Clinician", "Dietitian", "Midwife",
    "Social Worker", "Social Services", "Acupuncturist", "Chaplain",
    "Medicine",        # Addiction Medicine, Family Medicine, Internal Medicine, etc.
    "Physic",          # Catches Physicist, Physical Therapist, Physiologist
    "Clinical",

    # RN patterns (safe - won't false-positive on "intern" like bare "RN" would)
    "Staff RN", "Charge RN", "Unit RN",
    # Medical abbreviations
    "LVN", "LPN", "CNA",
    "LCSW",            # Licensed Clinical Social Worker
    "CRNA",            # Certified Registered Nurse Anesthetist
    "LPCC",            # Licensed Professional Clinical Counselor
    "LMFT",            # Licensed Marriage Family Therapist
    "CDRC",            # Chemical Dependency Recovery Counselor

    # =========================================================================
    # MEDICAL/CLINICAL - Specialties
    # =========================================================================
    "Audiolog",        # Audiologist, Audiology
    "Behavioral Health",
    "Cardiology", "Cardiologist", "Cardiac", "Cardiovascular",
    "Dermatology",
    "Dialysis",
    "Gastroenterology", "Gastrointestinal",
    "Gynecology", "OB/GYN", "Obstetrics", "Obstetrical",
    "Mental Health", "Mental Hlth",
    "Neonatal",
    "Oncology",
    "Ophthalmology", "Ophthalmic",
    "Optometrist", "Optometric", "Optical",
    "Orthopedic",
    "Pediatric",
    "Psychiatry", "Psychiatric", "Psycholog",  # Psychologist, Psychology, Psychological
    "Pulmonary",
    "Radiology", "Radiologic",
    "Rehabilitation", "Rehab Aide",
    "Respiratory",
    "Urology",
    "Vascular",
    "Dental", "Hygienist",
    "Veterinary",

    # =========================================================================
    # MEDICAL/CLINICAL - Procedures, Departments & Units
    # =========================================================================
    "Anesthesia",
    "Cath Lab",
    "Emergency Room", "ED Tech",  # Emergency Department Tech
    "Endoscopy", "Endo Tech",
    "Hospice", "Palliative",
    "Home Health",
    "ICU",
    "Imaging",
    "Infusion",
    "Inpatient", "Outpatient", "Ambulatory",
    "Labor and Delivery", "Labor & Delivery", "L&D",
    "Med Surg", "Med/Surg",
    "NICU", "PICU", "PACU",
    "Nuclear Medicine",
    "Operating Room", "OR Tech",  # Operating Room Tech
    "Perioperative",
    "Surgical", "Surgery", "Surg Tech",
    "Transplant",
    "Wound Care", "Wound Ostomy",

    # =========================================================================
    # MEDICAL/CLINICAL - Diagnostics, Imaging & Lab
    # =========================================================================
    "Echocardiograph", "Sonographer",
    "EKG", "EEG", "EMG",
    "Mammograph", "Mammo Tech",
    "MRI",
    "Neurodiagnostic",
    "Bone Dens",       # Bone Densitometry / Bone Density
    "Angiograph",      # Angiography / Angiogram
    "Pathologist", "Pathology",
    "Laboratory Assistant", "Lab Assistant", "Lab Technician",
    "CLS",             # Clinical Laboratory Scientist
    "Rad Tech",        # Radiologic Tech (abbreviated) - also catches Rad Technologist
    "CT Tech",         # CT Scan Technician
    "Special Procedure",  # Special Procedures is radiology imaging
    "Technologist",    # All "Technologist" roles in these scrapers are medical
    "Monitor Technician",
    "Histolog",        # Histology, Histologic, Histological
    "Phlebotom",       # Phlebotomist, Phlebotomy
    "Sterile Processing", "SPD",
    "Perfusionist",
    "Dosimetrist",
    "Embryologist",
    "Lactation",

    # =========================================================================
    # MEDICAL/CLINICAL - Programs, Care Management & Conditions
    # =========================================================================
    "Patient",         # All "Patient ___" titles are healthcare in these scrapers
    "Case Manager", "Case Management",
    "Care Manager", "Care Coordinator", "Care Management", "Care Aide",
    "Resident Care",   # Nursing home/assisted living
    "Health Coach", "Health Educator", "Health Education",
    "Wellness", "Population Health",
    "Chronic Conditions", "Disease Management",
    "Utilization Review", "QA Nurse",
    "Infection Prevent",   # Infection Prevention / Preventionist
    "Pelvic",
    "Childbirth", "Prenatal",
    "Postpartum", "Post Partum", "Perinatal",
    "Mother Baby", "Mom Baby",
    "OB Tech",
    "Substance",       # Substance Use Navigator, etc.
    "Addiction",        # Addiction Medicine
    "Child Life",
    "Cancer Registr",  # Cancer Registrar / Cancer Registry
    "Contact Lens",
    "Vision Services",
    "GI Tech",
    "Comparative Medicine",
    "Counselor", "Counseling",
    "Spiritual Care",
    "Speech",          # Speech Therapist, Speech Pathologist, etc.
    "Occupational",    # Occupational Therapist (not IT "Occupational Health")
    "PT Assist",       # Physical Therapy Assistant
    "Paramedic", "EMT",  # Emergency Medical Services

    # =========================================================================
    # FACILITY/SERVICE - Non-Tech Support Roles
    # =========================================================================
    "Housekeep",       # Housekeeping, Housekeeper
    "Attendant", "Cook", "Kitchen",
    "Gardener", "Storekeeper",
    "Ward Clerk", "Admitting", "Receptionist",
    "Administrative Coordinator",
    "Transcriptionist",
    "Environmental Services", "EVS",
    "Security Guard", "Security Officer",
    "Cashier",
    "Driver",
    "Transportation", "Transporter",
    "Staffing Coordinator",
    "House Supervisor",    # Hospital nursing supervisor (not IT)
    "Unit Secretary",
    "Food Service", "Nutrition",
    "Executive Assistant", "Executive Chef",

    # =========================================================================
    # EXECUTIVE/LEADERSHIP - Non-Tech
    # =========================================================================
    "Vice President", "SVP",
    "General Counsel", "Attorney",
    "Philanthropy", "Donor Relations",
]

# High-priority keywords for your background (used for AI pre-filter)
# INSTRUCTIONS: Add keywords that MUST be in the job title for you to be interested.
INTEREST_KEYWORDS = [
    "Cyber", "Security", "IT", "Analyst", "Systems", "Network", "Infrastructure",
    "Data", "Python", "Cloud", "Azure", "Engineering", "Operations", "Technical",
    "Support", "Compliance", "Warehouse", "Logistics", "Hardware", "Diagnostics"
]

# =============================================================================
# TITLE PRE-FILTER (before fetching descriptions)
# =============================================================================
# Only fetch description / analyze if title contains at least ONE of these (word match).
# Stops obvious non-tech (e.g. "Food Service Worker") from wasting fetches.
# Keep broad so you don't miss tech roles; add help desk / customer support.
TITLE_MUST_CONTAIN = [
    "IT", "Tech", "Security", "Cyber", "Analyst", "Engineer", "Developer",
    "Systems", "Network", "Data", "Software", "Support", "Customer Service",
    "Help Desk", "Compliance", "Infrastructure", "Operations", "Technical"
]

# Titles that are junk (e.g. search keyword returned as "job" by a scraper). Skip entirely.
BOGUS_TITLES = [
    "train", "trained", "trainers", "trains", "rotation", "rotational"
]

# =============================================================================
# CAREER PATH PRIORITIZATION ("Target Role Mode")
# =============================================================================
# This system helps you prioritize jobs that are stepping stones toward your
# dream role. It classifies every job into 4 tiers:
#
#   TARGET_DIRECT  = Jobs that ARE your target role (highest priority)
#   TARGET_ADJACENT = Jobs closely related to your target (high priority)
#   CAREER_FEEDER   = General IT/tech roles that build toward your target
#   AVOID           = Unrelated roles (still shown, but ranked lowest)
#
# HOW IT WORKS:
#   The system searches job titles and descriptions for keywords you define
#   in taxonomy.py. Jobs matching TARGET_DIRECT keywords rank highest,
#   TARGET_ADJACENT next, then CAREER_FEEDER, then everything else.
#
# HOW TO CUSTOMIZE FOR YOUR OWN CAREER PATH:
#   1. Open taxonomy.py
#   2. Edit SOC_DIRECT_KEYWORDS → put YOUR target role keywords
#      (Example for SOC analyst: "soc analyst", "incident response", "siem analyst")
#      (Example for DevOps: "devops", "site reliability", "platform engineer", "cicd")
#      (Example for Data Science: "data scientist", "machine learning", "ml engineer")
#   3. Edit SOC_ADJACENT → put related/stepping-stone role categories + keywords
#      (Example for SOC: NOC operations, SIEM tools, endpoint security)
#      (Example for DevOps: cloud ops, kubernetes, infrastructure automation)
#      (Example for Data Science: data analyst, business intelligence, ETL)
#   4. Edit IT_FEEDER_KEYWORDS → general tech roles that build foundational skills
#
# The default taxonomy.py is set up for SOC Analyst / Cybersecurity careers.
# See taxonomy.py for the full keyword lists and weights.
#
ENABLE_SOC_FEEDER_MODE = True

# Minimum feeder score to keep job (0-100, default 30 = include most roles)
# Higher = stricter filtering. 0 = include everything, 100 = only TARGET_DIRECT
MIN_FEEDER_SCORE_TO_KEEP = 30

# If True, include unpaid internships/apprenticeships in results
INCLUDE_UNPAID_INTERNSHIPS = True

# If True and a Help Desk/IT Support role has IT context keywords, keep it
# If False, filter all customer service roles as AVOID
ALLOW_HELP_DESK_WITH_IT_CONTEXT = True

# Expand keyword searches to include target-role-adjacent keywords
# When True, adds keywords from your taxonomy categories to each site search
EXPAND_SEARCHES_WITH_SOC_KEYWORDS = True

# Which taxonomy categories to prioritize in searches (order = priority)
# These must match category names in taxonomy.py's SOC_ADJACENT dict.
# Default categories (for SOC Analyst path):
SOC_FEEDER_SEARCH_PRIORITY = [
    "SIEM_LOGGING",          # Splunk, Elasticsearch, etc. - very high value
    "NOC_OPERATIONS",        # 24x7 monitoring, event triage
    "ENDPOINT_EDR",          # Crowdstrike, Defender, Intune
    "IAM_ACCESS",            # Active Directory, Okta, Azure AD
    "VULNERABILITY_PATCH",   # Patch management, vuln scanning
    "FIREWALL_NETWORK",      # Palo Alto, Cisco, network security
    "IT_SUPPORT_SECURITY",   # Help Desk with IT/security exposure
    "GRC_COMPLIANCE",        # Compliance, audit, policy (lower priority)
]
#
# EXAMPLE: If you were targeting DevOps instead of SOC, you'd create your own
# categories in taxonomy.py and list them here:
# SOC_FEEDER_SEARCH_PRIORITY = [
#     "CICD_AUTOMATION",       # Jenkins, GitHub Actions, ArgoCD
#     "CLOUD_INFRASTRUCTURE",  # AWS, GCP, Azure, Terraform
#     "CONTAINER_ORCHESTRATION", # Kubernetes, Docker, Helm
#     "MONITORING_OBSERVABILITY", # Datadog, Prometheus, Grafana
#     "SCRIPTING_AUTOMATION",  # Python, Bash, Ansible
# ]

# Override feeder weights per category (0-100, default uses taxonomy.py weights)
# Leave empty dict {} to use defaults from taxonomy.py
FEEDER_WEIGHT_OVERRIDES = {}

# Example customization:
# FEEDER_WEIGHT_OVERRIDES = {
#     "SIEM_LOGGING": 100,        # Highest priority
#     "NOC_OPERATIONS": 85,
#     "GRC_COMPLIANCE": 40,       # Lower priority if you want
# }

# =============================================================================
# SOC FEEDER KEYWORD EXPANSION (for SOC Feeder Mode searching)
# =============================================================================

# Max keywords to use per site during SOC Feeder Mode searches
# Higher = more comprehensive but slower + more API calls
# Recommended: 10-20 keywords per site
SOC_FEEDER_KEYWORDS_PER_SITE = 15

# Per-site keyword overrides (optional)
# Use to exclude certain SOC categories from specific sites
# Example: {"intel": {"exclude_categories": ["SIEM_LOGGING"]}}
SITE_KEYWORD_OVERRIDES = {}
