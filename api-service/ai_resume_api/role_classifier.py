"""Classify job descriptions by career domain and role level.

Used to select appropriate assessor personas for fit assessment.
Supports multiple career domains (technology, culinary, finance, etc.).
Add new domains by extending CAREER_DOMAINS.
"""

import re

import structlog

logger = structlog.get_logger(__name__)


# ---------------------------------------------------------------------------
# Career Domain Definitions
# ---------------------------------------------------------------------------

CAREER_DOMAINS = {
    "technology": {
        "keywords": [
            "software", "engineer", "infrastructure", "platform",
            "cloud", "distributed systems", "AI", "ML", "machine learning",
            "data", "DevOps", "SRE", "backend", "frontend", "full-stack",
            "API", "microservices", "kubernetes", "security", "cyber",
            "architecture", "scalable", "deployment", "CI/CD",
        ],
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
    "culinary": {
        "keywords": [
            "chef", "culinary", "kitchen", "menu", "fine dining", "gastronomy",
            "catering", "michelin", "food safety", "beverage", "hospitality",
            "pastry", "sous chef", "back of house", "BOH", "sanitation",
        ],
        "levels": {
            "c-suite": {
                "patterns": [
                    r"\bChief\s+Culinary\s+Officer\b",
                    r"\bCCO\b",
                    r"\bGroup\s+Executive\s+Chef\b",
                ],
                "persona": (
                    "You are a hospitality executive recruiter. You evaluate "
                    "candidates on global brand strategy, multi-unit P&L, and "
                    "culinary innovation at a corporate or international scale."
                ),
                "eval_criteria": [
                    "Multi-unit P&L management",
                    "Global brand consistency",
                    "Supply chain oversight",
                    "Executive leadership",
                ],
            },
            "director": {
                "patterns": [
                    r"\bExecutive\s+Chef\b",
                    r"\bDirector\s+of\s+Culinary\b",
                    r"\bHead\s+Chef\b",
                ],
                "persona": (
                    "You are a headhunter for elite restaurants. You look for "
                    "menu engineering, kitchen labor management, and high-volume "
                    "fine dining excellence."
                ),
                "eval_criteria": [
                    "Menu innovation",
                    "Kitchen operations",
                    "Cost control (Labor/COGS)",
                    "Staff mentoring",
                ],
            },
        },
    },
    "finance_trading": {
        "keywords": [
            "trader", "quant", "portfolio", "equity", "fixed income", "hedge fund",
            "arbitrage", "derivatives", "risk management", "alpha", "execution",
            "algorithmic", "bloomberg", "backtesting", "fintech",
        ],
        "levels": {
            "c-suite": {
                "patterns": [
                    r"\bChief\s+Investment\s+Officer\b",
                    r"\bHead\s+of\s+Trading\b",
                ],
                "persona": (
                    "You are a high-finance executive recruiter. You evaluate "
                    "candidates on multi-billion dollar AUM strategy, risk appetite, "
                    "and regulatory compliance."
                ),
                "eval_criteria": [
                    "AUM Growth",
                    "Risk Framework Ownership",
                    "Regulatory Relations",
                    "Capital Allocation",
                ],
            },
            "ic-senior": {
                "patterns": [
                    r"\bSenior\s+Quantitative\s+Trader\b",
                    r"\bPortfolio\s+Manager\b",
                    r"\bQuant\s+Lead\b",
                ],
                "persona": (
                    "You are a quantitative talent specialist. You focus on "
                    "alpha generation, mathematical modeling, and consistent "
                    "P&L performance."
                ),
                "eval_criteria": [
                    "Sharpe Ratio/Performance",
                    "Algorithm Development",
                    "Market Microstructure Knowledge",
                ],
            },
        },
    },
    "life_sciences": {
        "keywords": [
            "drug discovery", "clinical", "biotech", "pharmacology", "R&D",
            "bioinformatics", "FDA", "regulatory", "molecular", "assay",
            "toxicology", "genetics", "laboratory", "IND", "GLP",
        ],
        "levels": {
            "director": {
                "patterns": [
                    r"\bDirector\s+of\s+Drug\s+Discovery\b",
                    r"\bHead\s+of\s+R&D\b",
                    r"\bClinical\s+Director\b",
                ],
                "persona": (
                    "You are a biotech recruiter. You evaluate the ability to "
                    "move candidates through the pipeline from discovery to "
                    "Phase I-III trials."
                ),
                "eval_criteria": [
                    "Pipeline Strategy",
                    "CRO Management",
                    "Regulatory Filing Success",
                    "Scientific Leadership",
                ],
            },
            "ic": {
                "patterns": [
                    r"\bResearch\s+Scientist\b",
                    r"\bPharmacologist\b",
                    r"\bLab\s+Manager\b",
                ],
                "persona": (
                    "You are a scientific recruiter focused on technical "
                    "methodology, data integrity, and laboratory execution."
                ),
                "eval_criteria": [
                    "Experimental Design",
                    "Data Analysis",
                    "Protocol Development",
                    "Technical Publications",
                ],
            },
        },
    },
    "healthcare": {
        "keywords": [
            "patient care", "nursing", "clinical operations", "EHR", "HIPAA",
            "diagnosis", "acute care", "medical board", "telehealth", "physician",
            "hospital", "outpatient", "oncology", "ICU",
        ],
        "levels": {
            "c-suite": {
                "patterns": [
                    r"\bChief\s+Medical\s+Officer\b",
                    r"\bChief\s+Nursing\s+Officer\b",
                    r"\bCNO\b",
                ],
                "persona": (
                    "You are a healthcare executive recruiter focusing on "
                    "clinical governance, patient safety metrics, and hospital "
                    "system integration."
                ),
                "eval_criteria": [
                    "Clinical Governance",
                    "Safety/Quality Metrics",
                    "Healthcare Economics",
                    "Staff Retention",
                ],
            },
            "manager": {
                "patterns": [
                    r"\bNurse\s+Manager\b",
                    r"\bClinic\s+Manager\b",
                    r"\bDepartment\s+Head\b",
                ],
                "persona": (
                    "You are a clinical lead recruiter focused on patient flow, "
                    "staff scheduling, and frontline compliance."
                ),
                "eval_criteria": [
                    "Patient Throughput",
                    "Unit Budgeting",
                    "Compliance Auditing",
                    "Clinical Mentoring",
                ],
            },
        },
    },
    "sales_growth": {
        "keywords": [
            "revenue", "quota", "SaaS", "account executive", "pipeline",
            "lead gen", "CRM", "growth", "partnerships", "closing",
            "B2B", "market share", "ARR", "salesforce",
        ],
        "levels": {
            "vp": {
                "patterns": [
                    r"\bVP\s+of\s+Sales\b",
                    r"\bHead\s+of\s+Revenue\b",
                ],
                "persona": (
                    "You are a growth-focused recruiter. You evaluate candidates "
                    "on scaling revenue, GTM strategy, and building high-velocity "
                    "sales machines."
                ),
                "eval_criteria": [
                    "ARR Growth",
                    "Sales Methodology Implementation",
                    "Global Expansion",
                    "Forecasting Accuracy",
                ],
            },
            "ic": {
                "patterns": [
                    r"\bAccount\s+Executive\b",
                    r"\bSales\s+Representative\b",
                    r"\bSDR\b",
                    r"\bBDR\b",
                ],
                "persona": (
                    "You are a sales recruiter focused on grit, activity metrics, "
                    "closing ratios, and relationship management."
                ),
                "eval_criteria": [
                    "Quota Attainment",
                    "Prospecting Skills",
                    "Negotiation",
                    "CRM Hygiene",
                ],
            },
        },
    },
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

# Minimum confidence gap between first and second domain to classify
# with high confidence. Below this threshold, secondary domain is reported.
_CONFIDENCE_GAP = 2


# ---------------------------------------------------------------------------
# Pre-compiled keyword patterns (word-boundary matching)
# ---------------------------------------------------------------------------
# Built once at import time to avoid recompiling on every request.

def _compile_keyword_patterns(domains: dict) -> dict[str, list[tuple[re.Pattern, str]]]:
    """Pre-compile word-boundary regex for each domain's keywords."""
    compiled = {}
    for domain, config in domains.items():
        patterns = []
        for kw in config["keywords"]:
            # Use word boundaries to prevent substring false positives.
            # re.IGNORECASE handles case-insensitive matching.
            pattern = re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE)
            patterns.append((pattern, kw))
        compiled[domain] = patterns
    return compiled


_KEYWORD_PATTERNS = _compile_keyword_patterns(CAREER_DOMAINS)


# ---------------------------------------------------------------------------
# Classification Functions
# ---------------------------------------------------------------------------

def _score_domain(jd_text: str, domain: str) -> int:
    """Count keyword matches for a domain using word-boundary regex."""
    return sum(1 for pattern, _ in _KEYWORD_PATTERNS[domain] if pattern.search(jd_text))


def classify_domain(job_description: str) -> dict:
    """Identify the career domain(s) from JD content using keyword frequency.

    Uses word-boundary matching to prevent substring false positives
    (e.g., "AI" no longer matches "catering").

    Returns:
        {
            "primary": "technology" | None,
            "secondary": "finance_trading" | None,
            "primary_score": 8,
            "secondary_score": 3,
            "confident": True,   # primary leads by >= _CONFIDENCE_GAP
        }
    """
    scores = {}
    for domain in CAREER_DOMAINS:
        score = _score_domain(job_description, domain)
        if score > 0:
            scores[domain] = score

    if not scores:
        return {
            "primary": None,
            "secondary": None,
            "primary_score": 0,
            "secondary_score": 0,
            "confident": False,
        }

    # Sort by score descending
    ranked = sorted(scores.items(), key=lambda x: x[1], reverse=True)

    primary, primary_score = ranked[0]
    secondary = None
    secondary_score = 0

    if len(ranked) > 1:
        secondary, secondary_score = ranked[1]

    # Require at least 3 keyword matches to classify
    if primary_score < 3:
        return {
            "primary": None,
            "secondary": None,
            "primary_score": primary_score,
            "secondary_score": secondary_score,
            "confident": False,
        }

    confident = (primary_score - secondary_score) >= _CONFIDENCE_GAP

    # Only report secondary if it also meets minimum threshold
    if secondary_score < 3:
        secondary = None
        confident = True  # No real competition

    return {
        "primary": primary,
        "secondary": secondary,
        "primary_score": primary_score,
        "secondary_score": secondary_score,
        "confident": confident,
    }


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
            "secondary_domain": "finance_trading" | None,
            "domain_confident": True,
            "level": "c-suite" | "vp" | ... | None,
            "jd_title": "Chief Technology Officer",
            "persona": "You are a ...",
            "eval_criteria": ["...", ...],
        }
    """
    jd_title = extract_jd_title(job_description)
    domain_result = classify_domain(job_description)
    domain = domain_result["primary"]

    if domain is None:
        logger.info(
            "role_classification",
            domain=None,
            level=None,
            jd_title=jd_title,
            primary_score=domain_result["primary_score"],
        )
        return {
            "domain": None,
            "secondary_domain": None,
            "domain_confident": False,
            "level": None,
            "jd_title": jd_title,
            "persona": FALLBACK_PERSONA,
            "eval_criteria": FALLBACK_CRITERIA,
        }

    level = classify_role_level(job_description, domain)

    if level is None:
        logger.info(
            "role_classification",
            domain=domain,
            secondary_domain=domain_result["secondary"],
            domain_confident=domain_result["confident"],
            level=None,
            jd_title=jd_title,
        )
        return {
            "domain": domain,
            "secondary_domain": domain_result["secondary"],
            "domain_confident": domain_result["confident"],
            "level": None,
            "jd_title": jd_title,
            "persona": FALLBACK_PERSONA,
            "eval_criteria": FALLBACK_CRITERIA,
        }

    level_config = CAREER_DOMAINS[domain]["levels"][level]

    logger.info(
        "role_classification",
        domain=domain,
        secondary_domain=domain_result["secondary"],
        domain_confident=domain_result["confident"],
        level=level,
        jd_title=jd_title,
        primary_score=domain_result["primary_score"],
        secondary_score=domain_result["secondary_score"],
    )

    return {
        "domain": domain,
        "secondary_domain": domain_result["secondary"],
        "domain_confident": domain_result["confident"],
        "level": level,
        "jd_title": jd_title,
        "persona": level_config["persona"],
        "eval_criteria": level_config["eval_criteria"],
    }
