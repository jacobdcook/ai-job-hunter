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
    "pge": True,       # Pacific Gas & Electric
    "smud": True,      # Sacramento Municipal Utility District
    "kaiser": True,    # Kaiser Permanente
    "state_ca": True,  # State of California (CalCareers)
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

# Keywords to search on State CA jobs site
# These will be searched separately and results combined
# Note: "Information" tends to return more IT results than just "IT"
STATE_CA_KEYWORDS = ["Information", "Security", "Analyst", "Systems", "Network", "Cyber"]

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

# Ignore these fields entirely.
# INSTRUCTIONS: Add any keywords here that you want to IMMEDIATELY discard.
# If you are looking for medical jobs, REMOVE the medical keywords below.
IGNORE_FIELDS = [
    # Default list excludes medical/clinical roles (useful for tech seekers)
    "Nurse", "Nursing", "Physician", "Medical Assistant", "Social Worker", 
    "Acupuncturist", "Pharmacist", "Pharmacy", "Therapist", "Social Services",
    "Patient Care", "Clinical", "LVN", "LPN", "Dietitian", "Surgical", "Imaging",
    "Radiology", "Anesthesia", "Behavioral Health", "Spiritual Care", "Chaplain",
    "Pathologist", "Laboratory Assistant", "CLS", "Rad Technologist", "Technologist",
    "Surg Tech", "Monitor Technician", "Emergency Room", "Cardiac", "Dialysis",
    "Oncology", "Psychiatric", "Counselor", "Lactation", "Embryologist", "Physic",
    "Midwife", "Dermatology", "Optometrist", "Ophthalmology", "Dental", "Hygienist",
    "Veterinary", "Respiratory", "Speech", "Occupational", "Rehabilitation", "Physical Therapist",
    "Echocardiograph", "Sonographer", "Pediatric", "OB/GYN", "Inpatient", "Outpatient",
    "Mental Health", "Psychologist", "Psychiatry", "Counseling", "CNA", "Home Health",
    "Urology", "Obstetrics", "Gynecology", "Surgery", "Perioperative", "Post-op",
    "Case Manager", "Case Management", "Utilization Review", "QA Nurse",
    "Chronic Conditions", "Disease Management", "Care Coordinator", "Care Management",
    "Health Coach", "Health Educator", "Wellness", "Population Health",
    # Facility/Service Roles
    "Housekeeping", "Attendant", "Cook", "Kitchen", "Gardener", "Storekeeper",
    "Ward Clerk", "Admitting Clerk", "Receptionist", 
    "Administrative Coordinator", "Transcriptionist", "Phlebotomist", "Sterile Processing",
    "Environmental Services", "EVS", "Security Guard", "Security Officer", "Cashier"
]

# High-priority keywords for your background (used for AI pre-filter)
# INSTRUCTIONS: Add keywords that MUST be in the job title for you to be interested.
INTEREST_KEYWORDS = [
    "Cyber", "Security", "IT", "Analyst", "Systems", "Network", "Infrastructure",
    "Data", "Python", "Cloud", "Azure", "Engineering", "Operations", "Technical",
    "Support", "Compliance", "Warehouse", "Logistics", "Hardware", "Diagnostics"
]
