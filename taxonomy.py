"""
SOC Feeder Path Taxonomy
Defines role categories and keywords for identifying SOC-adjacent/feeder roles.
"""

# ============================================================================
# SOC DIRECT - Roles that ARE the target (SOC, IR, DFIR, Threat Hunting)
# ============================================================================
SOC_DIRECT_KEYWORDS = [
    "soc analyst", "security operations analyst", "security operations center",
    "incident response", "ir analyst", "threat detection", "threat analyst",
    "blue team", "siem analyst", "security analyst", "cybersecurity analyst",
    "detection engineer", "security monitoring", "csirt", "cert team",
    "dfir", "digital forensics", "threat hunter", "threat hunting",
    "intrusion analyst", "malware analyst", "detection engineering"
]

# ============================================================================
# SOC ADJACENT - High-value feeder roles with weights
# ============================================================================
SOC_ADJACENT = {
    "NOC_OPERATIONS": {
        "weight": 90,
        "keywords": [
            "noc", "network operations center", "network operations", "operations center",
            "event monitoring", "alert triage", "24x7", "shift work", "on-call",
            "monitoring", "operations analyst", "network analyst", "monitoring specialist",
            "event management", "ticket management", "tier 1", "tier 2"
        ]
    },
    "IAM_ACCESS": {
        "weight": 85,
        "keywords": [
            "iam", "identity", "access management", "okta", "azure ad", "entra",
            "active directory", "sso", "single sign-on", "mfa", "multi factor",
            "provisioning", "deprovisioning", "rbac", "sailpoint", "access control",
            "directory services", "privileged access", "pam"
        ]
    },
    "ENDPOINT_EDR": {
        "weight": 85,
        "keywords": [
            "edr", "endpoint detection", "crowdstrike", "sentinelone", "carbon black",
            "defender for endpoint", "intune", "mdm", "mobile device management",
            "endpoint", "hardening", "patching", "gpo", "group policy",
            "configuration management", "asset management", "vulnerability management"
        ]
    },
    "VULNERABILITY_PATCH": {
        "weight": 80,
        "keywords": [
            "vulnerability", "vuln", "nessus", "tenable", "qualys", "rapid7",
            "scanner", "patch management", "remediation", "cve", "exposure",
            "risk management", "threat assessment", "scanning"
        ]
    },
    "FIREWALL_NETWORK": {
        "weight": 80,
        "keywords": [
            "firewall", "palo alto", "fortinet", "fortigate", "cisco", "juniper",
            "vpn", "ids", "intrusion detection", "ips", "intrusion prevention",
            "proxy", "zscaler", "network security", "network infrastructure",
            "security infrastructure", "traffic analysis"
        ]
    },
    "SIEM_LOGGING": {
        "weight": 95,
        "keywords": [
            "splunk", "sentinel", "elastic", "kibana", "sumo logic", "datadog",
            "dynatrace", "new relic", "log analysis", "syslog", "sigma rules",
            "kql", "kusto", "siem", "logging", "observability", "centralized logging",
            "log management", "event correlation"
        ]
    },
    "GRC_COMPLIANCE": {
        "weight": 60,
        "keywords": [
            "grc", "governance", "risk", "compliance", "audit", "auditor",
            "soc 2", "iso 27001", "iso 27002", "nist", "cis", "hipaa", "pci-dss",
            "policy", "controls", "frameworks", "compliance analyst"
        ]
    },
    "IT_SUPPORT_SECURITY": {
        "weight": 70,
        "keywords": [
            "help desk", "helpdesk", "service desk", "it support", "technical support",
            "desktop support", "end user support", "tier 1", "tier 2", "tier 3",
            "support analyst", "support technician", "support specialist",
            "tickets", "troubleshooting", "active directory", "azure ad", "m365",
            "office 365", "intune", "vpn", "network", "security"
        ]
    }
}

# ============================================================================
# IT FEEDER - Core IT fundamentals that lead to security
# ============================================================================
IT_FEEDER_KEYWORDS = [
    "junior systems administrator", "systems administrator", "sysadmin",
    "junior network administrator", "network administrator",
    "it analyst", "it technician", "it specialist", "it support",
    "systems engineer", "network engineer", "infrastructure engineer",
    "network technician", "support technician", "support specialist",
    "infrastructure analyst", "infrastructure technician",
    "windows server", "linux", "vmware", "hyper-v", "aws", "azure",
    "cloud infrastructure", "cloud operations", "devops"
]

# ============================================================================
# INTERNSHIPS / APPRENTICESHIPS / ROTATIONS (boost if present)
# ============================================================================
INTERNSHIP_KEYWORDS = [
    "intern", "internship", "apprentice", "apprenticeship",
    "trainee", "training program", "rotational", "rotation",
    "associate", "junior", "entry level", "entry-level",
    "graduate", "new grad", "recent grad", "residency", "fellowship",
    "co-op", "cooperative education"
]

# ============================================================================
# SHIFT-BASED / 24X7 / ON-CALL (strong SOC signal)
# ============================================================================
SHIFT_KEYWORDS = [
    "24x7", "24/7", "around the clock", "shift work", "shift", "on-call",
    "weekends", "holidays", "rotating shift", "swing shift", "night shift",
    "graveyard", "first shift", "second shift", "third shift"
]

# ============================================================================
# HARD EXCLUSIONS - Dead-end roles (filtered out unless IT context present)
# ============================================================================
HARD_EXCLUDE_KEYWORDS = [
    "customer service representative", "customer service specialist",
    "call center", "call center representative",
    "sales representative", "sales associate", "account executive",
    "retail", "retail associate", "cashier", "store associate",
    "teller", "bank teller",
    "nurse", "nursing", "registered nurse", "rn", "lvn", "lpn", "cna",
    "medical assistant", "physician assistant", "healthcare",
    "pharmacy", "pharmacist", "pharmacy technician",
    "patient", "patient advocate", "patient care",
    "warehouse", "warehouse associate", "warehouse worker", "logistics",
    "driver", "delivery driver",
    "janitor", "housekeeper", "custodian",
    "food service", "cook", "kitchen",
    "security guard", "loss prevention", "security officer",
    "legal assistant", "paralegal", "attorney",
    "hr specialist", "human resources", "recruiter",
    "accountant", "bookkeeper", "accounting"
]

# ============================================================================
# CONTEXT RULES - If title has IT support BUT description has these, it's IT_FEEDER
# ============================================================================
IT_CONTEXT_KEYWORDS = [
    "active directory", "azure", "m365", "intune", "vpn", "network",
    "tickets", "endpoint", "security", "siem", "firewall", "linux",
    "windows server", "infrastructure", "compliance", "audit"
]


def classify_job(title: str, description: str = "") -> dict:
    """
    Classify a job based on title and description.

    Returns:
        {
            'category': 'SOC_DIRECT' | 'SOC_ADJACENT' | 'IT_FEEDER' | 'AVOID',
            'subcategory': specific feeder type if applicable,
            'matched_keywords': list of keywords that matched,
            'feeder_score': 0-100,
            'reasons': list of reason strings,
            'is_internship': bool,
            'is_shift_based': bool
        }
    """
    title_lower = title.lower()
    desc_lower = description.lower()
    full_text = (title + " " + description).lower()

    matched = []
    reasons = []

    # Check for hard exclusions
    for keyword in HARD_EXCLUDE_KEYWORDS:
        if keyword in title_lower or keyword in desc_lower:
            # Exception: if it's IT support with IT context, don't exclude
            if "help desk" in title_lower or "it support" in title_lower or "support technician" in title_lower:
                has_context = any(ctx in desc_lower for ctx in IT_CONTEXT_KEYWORDS)
                if has_context:
                    break
            reasons.append(f"Matched exclusion: '{keyword}'")
            return {
                'category': 'AVOID',
                'subcategory': 'hard_exclude',
                'matched_keywords': matched,
                'feeder_score': 0,
                'reasons': reasons,
                'is_internship': False,
                'is_shift_based': False
            }

    # Check for SOC_DIRECT
    direct_matches = []
    for keyword in SOC_DIRECT_KEYWORDS:
        if keyword in title_lower:
            matched.append(keyword)
            direct_matches.append(keyword)

    if direct_matches:
        return {
            'category': 'SOC_DIRECT',
            'subcategory': 'direct_soc_role',
            'matched_keywords': matched,
            'feeder_score': 100,
            'reasons': [f"SOC Direct role: {', '.join(direct_matches)}"],
            'is_internship': any(k in title_lower for k in INTERNSHIP_KEYWORDS),
            'is_shift_based': any(k in full_text for k in SHIFT_KEYWORDS)
        }

    # Check for SOC_ADJACENT by category
    adjacent_matches = {}
    best_category = None
    best_weight = 0

    for category, config in SOC_ADJACENT.items():
        category_matches = []
        for keyword in config['keywords']:
            if keyword in title_lower or keyword in desc_lower:
                category_matches.append(keyword)

        if category_matches:
            adjacent_matches[category] = category_matches
            if config['weight'] > best_weight:
                best_weight = config['weight']
                best_category = category

    if best_category:
        matched.extend(adjacent_matches[best_category])
        reasons.append(f"SOC Adjacent ({best_category}): {', '.join(adjacent_matches[best_category])}")

        return {
            'category': 'SOC_ADJACENT',
            'subcategory': best_category,
            'matched_keywords': matched,
            'feeder_score': best_weight,
            'reasons': reasons,
            'is_internship': any(k in title_lower for k in INTERNSHIP_KEYWORDS),
            'is_shift_based': any(k in full_text for k in SHIFT_KEYWORDS)
        }

    # Check for IT_FEEDER
    feeder_matches = []
    for keyword in IT_FEEDER_KEYWORDS:
        if keyword in title_lower or keyword in desc_lower:
            matched.append(keyword)
            feeder_matches.append(keyword)

    if feeder_matches:
        reasons.append(f"IT Feeder role: {', '.join(feeder_matches)}")
        return {
            'category': 'IT_FEEDER',
            'subcategory': 'core_it_fundamentals',
            'matched_keywords': matched,
            'feeder_score': 50,
            'reasons': reasons,
            'is_internship': any(k in title_lower for k in INTERNSHIP_KEYWORDS),
            'is_shift_based': any(k in full_text for k in SHIFT_KEYWORDS)
        }

    # No match - AVOID
    return {
        'category': 'AVOID',
        'subcategory': 'unrelated_role',
        'matched_keywords': matched,
        'feeder_score': 0,
        'reasons': ["No SOC or IT feeder keywords detected"],
        'is_internship': any(k in title_lower for k in INTERNSHIP_KEYWORDS),
        'is_shift_based': any(k in full_text for k in SHIFT_KEYWORDS)
    }


def calculate_priority_score(groq_score: int, feeder_score: int, is_internship: bool, is_shift_based: bool) -> float:
    """
    Calculate combined priority score for ranking.

    Args:
        groq_score: Groq AI match score (1-10)
        feeder_score: SOC feeder path score (0-100)
        is_internship: True if internship/apprenticeship/rotation
        is_shift_based: True if 24x7/shift work

    Returns:
        Combined priority score (0-100)
    """
    # Base: 55% AI relevance + 45% SOC feeder fit
    base_score = (groq_score * 10) * 0.55 + feeder_score * 0.45

    # Boosts
    if is_internship:
        base_score += 10
    if is_shift_based:
        base_score += 8

    return min(100, base_score)
