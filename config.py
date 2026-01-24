YOUR_BACKGROUND = """
- Name: Jacob Cook
- Education: B.S. in Computer Science (CSUS/Sac State), starting MS in Cybersecurity (WGU) soon.
- Certifications: CompTIA Security+ Certified.
- Core Skills: Python, Linux, SIEM (Wazuh), Log Analysis, Incident Response, Cloud Security (Azure/Terraform).
- Key Projects: 
  * Blue Team SOC Lab: Wazuh SIEM for threat detection & log analysis.
  * SOAR-lite: Incident Response Orchestrator for automated threat mitigation.
  * AI Log Auditor: Automated log analysis with AI-powered detection.
  * Cloud Auditor: Security auditing for Terraform and Azure infrastructure.
  * Network Traffic Behavioral Analyzer: Detects C2 beaconing using behavioral analysis.
- Work History: 5+ years in Industrial Operations/Engineering Support (Target Warehouse) handling hardware diagnostics, change management, and technical troubleshooting.
- Target Roles: SOC Analyst, Security Analyst, Junior Security Engineer, IT Analyst, or entry-level Infrastructure/Operations roles.
"""

# =============================================================================
# JOB SITES CONFIGURATION
# =============================================================================
ENABLED_SITES = {
    "pge": True,      # Pacific Gas & Electric
    "smud": False,    # Sacramento Municipal Utility District (set to True when ready)
}

# These keywords will be used for searching the PG&E site
SEARCH_QUERIES = [
    "Security", "Cyber", "Associate", "Trainee", "Apprentice", 
    "Customer Service", "Representative", "RDP", "Rotation", "Rotational",
    "IT Analyst", "Systems Analyst", "Infrastructure", "Compliance",
    "Network", "Support", "Technician", "Operations Analyst",
    "Intern", "Internship"
]

# These titles are always kept even if they contain noise keywords
ENTRY_LEVEL_INDICATORS = [
    "Associate", "Junior", "Entry", "Trainee", "Apprentice", 
    "Rotational", "Rotation", "RDP", "Representative", "Service", 
    "Clerk", "Support", "Technician", "Analyst I", "Level 1",
    "Intern", "Internship"
]

# These keywords trigger the noise filter
NOISE_KEYWORDS = ["Senior", "Expert", "Principal", "Lead", "Chief", "Director", "Manager"]
