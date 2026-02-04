"""Classify job descriptions by career domain and role level.

Used to select appropriate assessor personas for fit assessment.
Currently supports the 'technology' domain. Add new domains by
extending CAREER_DOMAINS.
"""

import re

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Career Domain Definitions
# ---------------------------------------------------------------------------

CAREER_DOMAINS = {
    "technology": {
        # Keywords that signal this JD belongs to the technology domain.
        # Matched case-insensitively against the full JD text.
        "keywords": [
            "software", "engineer", "infrastructure", "platform",
            "cloud", "distributed systems", "AI", "ML", "machine learning",
            "data", "DevOps", "SRE", "backend", "frontend", "full-stack",
            "API", "microservices", "kubernetes", "security", "cyber",
            "architecture", "scalable", "deployment", "CI/CD",
        ],
        # Role levels ordered from most senior to least senior.
        # First match wins, so more specific patterns come first.
        "levels": {
            "c-suite": {
                "patterns": [
                    r"\bC[A-Z]O\b",                           # CTO, CIO, CISO, CPO, CDO
                    r"\bChief\s+\w+\s+Officer\b",              # Chief Technology Officer
                    r"\bChief\s+Architect\b",
                ],
                "persona": (
                    "You are a board-level executive recruiter who has placed "
                    "hundreds of C-suite technology leaders. You evaluate candidates "
                    "against the full scope of a C-level role: org-wide technical "
                    "strategy, board and investor communication, P&L ownership, "
                    "company-scale decision-making, and industry thought leadership. "
                    "A VP applying for a C-suite role is a level jump that must be "
                    "acknowledged — assess whether the candidate has operated at "
                    "C-level scope even if the title was VP."
                ),
                "eval_criteria": [
                    "Org-wide technical strategy ownership",
                    "Board/investor/external stakeholder experience",
                    "P&L or budget authority at company scale",
                    "Team scale (100+ engineers typical for CTO)",
                    "Industry presence and thought leadership",
                    "Prior C-level or equivalent scope",
                ],
            },
            "vp": {
                "patterns": [
                    r"\b(?:Senior\s+)?Vice\s+President\b",
                    r"\bSVP\b",
                    r"\bVP\b(?:\s+of)?\s+\w+",
                ],
                "persona": (
                    "You are a senior leadership recruiter specializing in VP-level "
                    "engineering placements. You evaluate candidates on department-scale "
                    "ownership: cross-functional leadership, budget authority, team "
                    "scaling (typically 30-100+ engineers), and the ability to translate "
                    "business strategy into technical execution. A Director applying "
                    "for VP is a scope jump — assess whether they have demonstrated "
                    "VP-level breadth."
                ),
                "eval_criteria": [
                    "Department-scale ownership",
                    "Cross-functional leadership",
                    "Budget authority and resource allocation",
                    "Team scale (30-100+ engineers)",
                    "Strategic planning and roadmap ownership",
                    "Executive communication",
                ],
            },
            "director": {
                "patterns": [
                    r"\b(?:Senior\s+)?Director\b",
                    r"\bHead\s+of\s+\w+",
                ],
                "persona": (
                    "You are a technical leadership recruiter focused on Director-level "
                    "roles. You evaluate candidates on domain ownership: technical "
                    "strategy within a product area, team building (typically 10-40 "
                    "engineers), hiring and retention, and the ability to drive "
                    "multi-quarter initiatives from concept to delivery."
                ),
                "eval_criteria": [
                    "Domain/product-area technical ownership",
                    "Team building and retention (10-40 engineers)",
                    "Multi-quarter initiative delivery",
                    "Technical roadmap creation",
                    "Stakeholder management",
                    "Hiring and mentoring",
                ],
            },
            "manager": {
                "patterns": [
                    r"\b(?:Senior\s+)?(?:Engineering\s+)?Manager\b",
                    r"\bTeam\s+Lead\b",
                    r"\bTech\s+Lead\s+Manager\b",
                ],
                "persona": (
                    "You are a technical hiring manager recruiter. You evaluate "
                    "candidates on team delivery: sprint execution, people management, "
                    "mentoring, project planning, and the ability to shield the team "
                    "while maintaining stakeholder alignment. Team size is typically "
                    "5-15 engineers."
                ),
                "eval_criteria": [
                    "People management and mentoring",
                    "Project delivery and execution",
                    "Team health and retention",
                    "Stakeholder communication",
                    "Technical decision-making",
                    "Hiring and onboarding",
                ],
            },
            "ic-senior": {
                "patterns": [
                    r"\bStaff\s+Engineer\b",
                    r"\bPrincipal\s+Engineer\b",
                    r"\bDistinguished\s+Engineer\b",
                    r"\bFellow\b",
                    r"\bSenior\s+Staff\b",
                    r"\bArchitect\b",
                ],
                "persona": (
                    "You are a technical recruiter specializing in senior IC roles. "
                    "You evaluate candidates on technical depth, system design at "
                    "scale, cross-team influence without authority, mentoring, and "
                    "the ability to drive architectural decisions across an organization."
                ),
                "eval_criteria": [
                    "System design at scale",
                    "Cross-team technical influence",
                    "Architectural decision-making",
                    "Mentoring and technical leadership",
                    "Deep domain expertise",
                    "Track record of shipped complex systems",
                ],
            },
            "ic": {
                "patterns": [
                    r"\b(?:Senior\s+)?(?:Software\s+)?Engineer\b",
                    r"\bDeveloper\b",
                    r"\bSRE\b",
                    r"\bDevOps\s+Engineer\b",
                ],
                "persona": (
                    "You are a technical recruiter evaluating individual contributor "
                    "candidates. You focus on hands-on technical skills, relevant "
                    "technology experience, problem-solving ability, and growth "
                    "trajectory."
                ),
                "eval_criteria": [
                    "Relevant technology stack experience",
                    "Hands-on coding and system skills",
                    "Problem-solving and debugging",
                    "Collaboration and communication",
                    "Growth trajectory",
                    "Domain knowledge",
                ],
            },
        },
    },
    # Future domains can be added here:
    # "culinary": { "keywords": [...], "levels": { ... } },
    # "finance": { "keywords": [...], "levels": { ... } },
}

# Fallback when no domain or level matches
FALLBACK_PERSONA = (
    "You are an experienced recruiter providing honest, calibrated fit "
    "assessments. You compare the candidate's background against the role "
    "requirements and assess seniority alignment."
)

FALLBACK_CRITERIA = [
    "Relevant experience",
    "Seniority alignment",
    "Skills match",
    "Domain knowledge",
]


# ---------------------------------------------------------------------------
# Classification Functions
# ---------------------------------------------------------------------------

def classify_domain(job_description: str) -> str | None:
    """Identify the career domain from JD content using keyword frequency.

    Returns the domain key (e.g., "technology") or None if no domain
    matches with sufficient confidence.
    """
    jd_lower = job_description.lower()
    best_domain = None
    best_score = 0

    for domain, config in CAREER_DOMAINS.items():
        score = sum(1 for kw in config["keywords"] if kw.lower() in jd_lower)
        if score > best_score:
            best_score = score
            best_domain = domain

    # Require at least 3 keyword matches to avoid false classification
    if best_score >= 3:
        return best_domain
    return None


def classify_role_level(job_description: str, domain: str) -> str | None:
    """Identify the role level within a domain using title pattern matching.

    Returns the level key (e.g., "c-suite", "vp") or None.
    Patterns are tested from most senior to least senior; first match wins.
    """
    levels = CAREER_DOMAINS[domain]["levels"]

    for level_key, level_config in levels.items():
        for pattern in level_config["patterns"]:
            if re.search(pattern, job_description, re.IGNORECASE):
                return level_key

    return None


def extract_jd_title(job_description: str) -> str:
    """Extract the job title from the first non-empty line of the JD."""
    for line in job_description.strip().split("\n"):
        line = line.strip()
        if line and len(line) < 120:
            return line
    return "Unknown Role"


def classify_job_description(job_description: str) -> dict:
    """Classify a job description and return the assessor configuration.

    Returns:
        {
            "domain": "technology" | None,
            "level": "c-suite" | "vp" | ... | None,
            "jd_title": "Chief Technology Officer",
            "persona": "You are a ...",
            "eval_criteria": ["...", ...],
        }
    """
    jd_title = extract_jd_title(job_description)
    domain = classify_domain(job_description)

    if domain is None:
        logger.info("role_classification", domain=None, level=None, jd_title=jd_title)
        return {
            "domain": None,
            "level": None,
            "jd_title": jd_title,
            "persona": FALLBACK_PERSONA,
            "eval_criteria": FALLBACK_CRITERIA,
        }

    level = classify_role_level(job_description, domain)

    if level is None:
        logger.info("role_classification", domain=domain, level=None, jd_title=jd_title)
        return {
            "domain": domain,
            "level": None,
            "jd_title": jd_title,
            "persona": FALLBACK_PERSONA,
            "eval_criteria": FALLBACK_CRITERIA,
        }

    level_config = CAREER_DOMAINS[domain]["levels"][level]

    logger.info(
        "role_classification",
        domain=domain,
        level=level,
        jd_title=jd_title,
    )

    return {
        "domain": domain,
        "level": level,
        "jd_title": jd_title,
        "persona": level_config["persona"],
        "eval_criteria": level_config["eval_criteria"],
    }
