"""
Configuration Template for AI Job Hunter

INSTRUCTIONS:
1. Copy this file and rename it to 'config.py'
2. Fill in YOUR_BACKGROUND with your own info
3. Customize SEARCH_QUERIES for the types of jobs you want
4. Adjust ENTRY_LEVEL_INDICATORS and NOISE_KEYWORDS as needed
"""

YOUR_BACKGROUND = """
- Name: [Your Name]
- Education: [Your Degree(s) and School(s)]
- Certifications: [Any certs you have - e.g., CompTIA Security+, AWS, etc.]
- Core Skills: [List your top 5-10 technical skills]
- Key Projects: 
  * [Project 1]: Brief description
  * [Project 2]: Brief description
  * [Project 3]: Brief description
- Work History: [Brief summary of relevant work experience]
- Target Roles: [Types of jobs you're looking for]
"""

# =============================================================================
# SEARCH QUERIES
# =============================================================================
# These keywords will be used for searching job sites.
# Add terms that match your target roles.

SEARCH_QUERIES = [
    # Security/IT focused
    "Security", "Cyber", "IT Analyst", "Systems Analyst",
    
    # Entry-level / foot-in-the-door
    "Associate", "Trainee", "Apprentice", "Intern", "Internship",
    
    # Customer-facing (good for getting hired)
    "Customer Service", "Representative", "Support",
    
    # Technical
    "Technician", "Infrastructure", "Network",
    
    # Programs
    "Rotation", "Rotational", "RDP",
    
    # Other
    "Compliance", "Operations Analyst"
]

# =============================================================================
# FILTERS
# =============================================================================

# Jobs with these words in the title are ALWAYS kept (overrides noise filter)
ENTRY_LEVEL_INDICATORS = [
    "Associate", "Junior", "Entry", "Trainee", "Apprentice", 
    "Rotational", "Rotation", "RDP", "Representative", "Service", 
    "Clerk", "Support", "Technician", "Analyst I", "Level 1",
    "Intern", "Internship"
]

# Jobs with these words in the title are filtered OUT (unless they have an entry-level indicator)
NOISE_KEYWORDS = [
    "Senior", "Expert", "Principal", "Lead", "Chief", "Director", "Manager"
]

# =============================================================================
# JOB SITES CONFIGURATION
# =============================================================================
# Enable/disable which job sites to search

ENABLED_SITES = {
    "pge": True,      # Pacific Gas & Electric
    "smud": False,    # Sacramento Municipal Utility District (coming soon)
    # Add more sites here as they're implemented
}
