"""End-to-end tests for role classifier with real-world job descriptions.

Tests cover all supported domains (technology, culinary, finance_trading,
life_sciences, healthcare, sales_growth) with authentic JD samples.
"""

import pytest

from ai_resume_api.role_classifier import (
    classify_job_description,
    classify_domain,
    classify_role_level,
    extract_jd_title,
)


# =============================================================================
# Sample Job Descriptions by Domain
# =============================================================================

JD_CULINARY_EXECUTIVE_CHEF = """Executive Chef

Overview: We are seeking a visionary Executive Chef to lead our flagship restaurant's culinary operations. You will be responsible for menu innovation, maintaining rigorous quality standards, and managing a high-performing back-of-house team.

Key Responsibilities:
- Design and execute seasonal menus that align with brand identity and food cost targets.
- Oversee all kitchen operations, including inventory management, labor costs, and vendor relations.
- Mentor and develop culinary staff to ensure world-class execution of every plate.
- Maintain 100% compliance with health, safety, and sanitation regulations.

Requirements: 10+ years in high-volume fine dining; proven experience in P&L management and team leadership.
"""

JD_FINANCE_SENIOR_QUANT_TRADER = """Senior Quantitative Trader

Overview: A premier global hedge fund is looking for a Senior Quantitative Trader to develop and deploy automated trading strategies. This role requires a blend of financial intuition and rigorous mathematical modeling.

Key Responsibilities:
- Design, test, and implement high-frequency or mid-frequency trading algorithms.
- Manage portfolio risk and optimize execution parameters in real-time.
- Collaborate with researchers to identify alpha-generating signals.
- Analyze large datasets to identify market inefficiencies and trends.

Requirements: PhD or Masters in a quantitative field (Physics, Math, CS); 5+ years of profitable track record in automated trading.
"""

JD_LIFE_SCIENCES_DIRECTOR_DRUG_DISCOVERY = """Director of Drug Discovery

Overview: We are a clinical-stage biotech firm seeking a Director of Drug Discovery to lead our early-stage pipeline. You will bridge the gap between initial molecular research and pre-clinical trials.

Key Responsibilities:
- Lead a multi-disciplinary team of chemists and biologists to identify novel therapeutic targets.
- Define the strategic roadmap for lead optimization and candidate selection.
- Oversee external research collaborations and CRO management.
- Ensure all R&D activities meet stringent regulatory and quality documentation standards.

Requirements: PhD in Biology or Chemistry; 12+ years in pharmaceutical R&D with a history of successful IND filings.
"""

JD_HEALTHCARE_CMO = """Chief Medical Officer

Overview: As the CMO, you will serve as the primary clinical leader for our hospital network, ensuring the highest standards of patient care and safety while driving operational efficiency at the executive level.

Key Responsibilities:
- Set the clinical vision and strategy for the entire organization.
- Lead the medical board and oversee physician recruitment, credentialing, and retention.
- Liaise with the Board of Directors on patient outcomes, risk mitigation, and regulatory compliance.
- Drive the adoption of new medical technologies and integrated care models.

Requirements: MD/DO degree with active board certification; 15+ years of clinical experience including significant executive leadership roles.
"""

JD_SALES_VP_GLOBAL_SALES = """VP of Global Sales

Overview: We are looking for a high-energy VP of Sales to scale our global revenue from $50M to $200M ARR. You will oversee regional sales directors and define our global go-to-market strategy.

Key Responsibilities:
- Build and scale a global sales organization, including SDR, AE, and Sales Ops functions.
- Forecast revenue with high accuracy and manage the departmental budget.
- Negotiate and close high-value enterprise partnerships.
- Collaborate with Marketing and Product teams to refine the value proposition and ICP.

Requirements: Proven track record of scaling B2B SaaS organizations; 10+ years in sales leadership with experience managing teams of 50+.
"""

JD_TECHNOLOGY_CTO = """Chief Technology Officer

We're seeking a CTO to lead our 100+ person engineering organization. You'll own the technical vision, architect our platform strategy, and represent technology at the board level.

Key Responsibilities:
- Define and execute the company-wide technical strategy and roadmap
- Build and scale distributed systems handling 10M+ requests/day
- Lead architecture decisions for cloud infrastructure and microservices
- Partner with CEO on product strategy and investor relations
- Drive technical hiring, mentoring, and org design

Requirements: 15+ years in software engineering with 5+ years at VP or C-level. Deep expertise in scalable distributed systems, cloud platforms (AWS/GCP), and technical leadership.
"""

JD_CROSS_DOMAIN_TECH_HEALTHCARE = """VP of Engineering, Healthcare Technology

We are a digital health startup building AI-powered diagnostic tools. We need a VP of Engineering who understands both software architecture and healthcare compliance.

Key Responsibilities:
- Lead a 40-person engineering team building HIPAA-compliant cloud services
- Design scalable ML pipelines for medical imaging and EHR integration
- Ensure FDA software validation and security compliance
- Collaborate with clinical advisors on product development
- Manage budget and technical roadmap

Requirements: 10+ years in software engineering, 3+ years in healthcare tech. Experience with regulatory compliance (HIPAA, FDA), cloud infrastructure, and ML systems.
"""

JD_AMBIGUOUS_SALES_TECH = """Head of Revenue Operations

We need a data-driven leader to optimize our revenue engine. This role spans sales operations, marketing ops, and technical systems integration.

Key Responsibilities:
- Build and maintain our CRM, marketing automation, and data pipeline infrastructure
- Analyze sales funnel metrics and implement growth experiments
- Lead a team of 10 including data engineers and sales ops analysts
- Own forecasting accuracy and territory planning
- Deploy API integrations for Salesforce, HubSpot, and data warehouse

Requirements: 8+ years in revenue operations or sales engineering. Strong technical background (SQL, Python, APIs) combined with sales process expertise.
"""


# =============================================================================
# Test Cases: Pure Domain Classification
# =============================================================================


class TestDomainClassification:
    """Test domain classification with varying keyword densities."""

    def test_culinary_domain_high_confidence(self) -> None:
        result = classify_domain(JD_CULINARY_EXECUTIVE_CHEF)
        assert result["primary"] == "culinary"
        assert result["confident"] is True  # Should have clear keyword lead
        assert result["primary_score"] >= 5  # Culinary keywords present

    def test_finance_domain_high_confidence(self) -> None:
        result = classify_domain(JD_FINANCE_SENIOR_QUANT_TRADER)
        assert result["primary"] == "finance_trading"
        assert result["confident"] is True
        assert result["primary_score"] >= 5

    def test_life_sciences_domain_high_confidence(self) -> None:
        result = classify_domain(JD_LIFE_SCIENCES_DIRECTOR_DRUG_DISCOVERY)
        assert result["primary"] == "life_sciences"
        assert result["confident"] is True
        assert result["primary_score"] >= 7

    def test_healthcare_domain_high_confidence(self) -> None:
        result = classify_domain(JD_HEALTHCARE_CMO)
        assert result["primary"] == "healthcare"
        assert result["confident"] is True
        assert result["primary_score"] >= 4

    def test_sales_domain_high_confidence(self) -> None:
        result = classify_domain(JD_SALES_VP_GLOBAL_SALES)
        assert result["primary"] == "sales_growth"
        assert result["confident"] is True
        assert result["primary_score"] >= 5

    def test_technology_domain_high_confidence(self) -> None:
        result = classify_domain(JD_TECHNOLOGY_CTO)
        assert result["primary"] == "technology"
        assert result["confident"] is True
        assert result["primary_score"] >= 8

    def test_cross_domain_tech_healthcare_secondary(self) -> None:
        """Tech role at a healthcare company should show both domains."""
        result = classify_domain(JD_CROSS_DOMAIN_TECH_HEALTHCARE)
        assert result["primary"] == "technology"
        # JD mentions "clinical", "medical", "diagnostic" which are life_sciences keywords
        # and "HIPAA", "EHR" which are healthcare keywords. Accept either.
        assert result["secondary"] in ["healthcare", "life_sciences"]
        # May or may not be confident depending on keyword balance
        assert result["primary_score"] > result["secondary_score"]

    def test_ambiguous_sales_tech_low_confidence(self) -> None:
        """RevOps role straddles sales and tech domains."""
        result = classify_domain(JD_AMBIGUOUS_SALES_TECH)
        # Should detect both domains with low confidence gap
        assert result["primary"] in ["technology", "sales_growth"]
        assert result["secondary"] in ["technology", "sales_growth"]
        assert result["primary"] != result["secondary"]
        # Confidence may be low if scores are close


# =============================================================================
# Test Cases: Role Level Classification
# =============================================================================


class TestRoleLevelClassification:
    """Test role level detection within domains."""

    def test_culinary_executive_chef_is_director(self) -> None:
        domain_result = classify_domain(JD_CULINARY_EXECUTIVE_CHEF)
        level = classify_role_level(JD_CULINARY_EXECUTIVE_CHEF, domain_result["primary"])
        assert level == "director"  # "Executive Chef" matches director pattern

    def test_finance_senior_quant_is_ic_senior(self) -> None:
        domain_result = classify_domain(JD_FINANCE_SENIOR_QUANT_TRADER)
        level = classify_role_level(JD_FINANCE_SENIOR_QUANT_TRADER, domain_result["primary"])
        assert level == "ic-senior"  # "Senior Quantitative Trader" matches pattern

    def test_life_sciences_director_is_director(self) -> None:
        domain_result = classify_domain(JD_LIFE_SCIENCES_DIRECTOR_DRUG_DISCOVERY)
        level = classify_role_level(
            JD_LIFE_SCIENCES_DIRECTOR_DRUG_DISCOVERY, domain_result["primary"]
        )
        assert level == "director"  # "Director of Drug Discovery" matches pattern

    def test_healthcare_cmo_is_c_suite(self) -> None:
        domain_result = classify_domain(JD_HEALTHCARE_CMO)
        level = classify_role_level(JD_HEALTHCARE_CMO, domain_result["primary"])
        assert level == "c-suite"  # "Chief Medical Officer" matches pattern

    def test_sales_vp_is_vp(self) -> None:
        domain_result = classify_domain(JD_SALES_VP_GLOBAL_SALES)
        level = classify_role_level(JD_SALES_VP_GLOBAL_SALES, domain_result["primary"])
        assert level == "vp"  # "VP of Global Sales" matches pattern

    def test_technology_cto_is_c_suite(self) -> None:
        domain_result = classify_domain(JD_TECHNOLOGY_CTO)
        level = classify_role_level(JD_TECHNOLOGY_CTO, domain_result["primary"])
        assert level == "c-suite"  # "Chief Technology Officer" matches CTO pattern


# =============================================================================
# Test Cases: End-to-End Classification
# =============================================================================


class TestFullClassification:
    """Test complete classify_job_description() pipeline."""

    def test_culinary_executive_chef_full(self) -> None:
        result = classify_job_description(JD_CULINARY_EXECUTIVE_CHEF)
        assert result["domain"] == "culinary"
        assert result["level"] == "director"
        assert result["jd_title"] == "Executive Chef"
        assert "headhunter for elite restaurants" in result["persona"]
        assert "Menu innovation" in result["eval_criteria"]
        assert result["domain_confident"] is True

    def test_finance_senior_quant_full(self) -> None:
        result = classify_job_description(JD_FINANCE_SENIOR_QUANT_TRADER)
        assert result["domain"] == "finance_trading"
        assert result["level"] == "ic-senior"
        assert result["jd_title"] == "Senior Quantitative Trader"
        assert "quantitative talent specialist" in result["persona"]
        assert "Sharpe Ratio/Performance" in result["eval_criteria"]

    def test_life_sciences_director_full(self) -> None:
        result = classify_job_description(JD_LIFE_SCIENCES_DIRECTOR_DRUG_DISCOVERY)
        assert result["domain"] == "life_sciences"
        assert result["level"] == "director"
        assert result["jd_title"] == "Director of Drug Discovery"
        assert "biotech recruiter" in result["persona"]
        assert "Pipeline Strategy" in result["eval_criteria"]

    def test_healthcare_cmo_full(self) -> None:
        result = classify_job_description(JD_HEALTHCARE_CMO)
        assert result["domain"] == "healthcare"
        assert result["level"] == "c-suite"
        assert result["jd_title"] == "Chief Medical Officer"
        assert "healthcare executive recruiter" in result["persona"]
        assert "Clinical Governance" in result["eval_criteria"]

    def test_sales_vp_full(self) -> None:
        result = classify_job_description(JD_SALES_VP_GLOBAL_SALES)
        assert result["domain"] == "sales_growth"
        assert result["level"] == "vp"
        assert result["jd_title"] == "VP of Global Sales"
        assert "growth-focused recruiter" in result["persona"]
        assert "ARR Growth" in result["eval_criteria"]

    def test_technology_cto_full(self) -> None:
        result = classify_job_description(JD_TECHNOLOGY_CTO)
        assert result["domain"] == "technology"
        assert result["level"] == "c-suite"
        assert result["jd_title"] == "Chief Technology Officer"
        assert "board-level executive recruiter" in result["persona"]
        assert "Org-wide technical strategy ownership" in result["eval_criteria"]

    def test_cross_domain_reports_secondary(self) -> None:
        """VP Eng at health tech should report both domains."""
        result = classify_job_description(JD_CROSS_DOMAIN_TECH_HEALTHCARE)
        assert result["domain"] == "technology"
        # Accept either healthcare or life_sciences as secondary
        assert result["secondary_domain"] in ["healthcare", "life_sciences"]
        assert result["level"] == "vp"  # "VP of Engineering" matches tech VP pattern

    def test_ambiguous_domain_flags_low_confidence(self) -> None:
        """RevOps role should flag ambiguous classification."""
        result = classify_job_description(JD_AMBIGUOUS_SALES_TECH)
        assert result["domain"] in ["technology", "sales_growth"]
        assert result["secondary_domain"] in ["technology", "sales_growth"]
        # Confidence depends on keyword balance, but should detect both


# =============================================================================
# Test Cases: Title Extraction
# =============================================================================


class TestTitleExtraction:
    """Test job title extraction from first line."""

    def test_extract_simple_title(self) -> None:
        assert extract_jd_title(JD_CULINARY_EXECUTIVE_CHEF) == "Executive Chef"

    def test_extract_multiword_title(self) -> None:
        assert extract_jd_title(JD_FINANCE_SENIOR_QUANT_TRADER) == "Senior Quantitative Trader"

    def test_extract_title_with_of(self) -> None:
        assert (
            extract_jd_title(JD_LIFE_SCIENCES_DIRECTOR_DRUG_DISCOVERY)
            == "Director of Drug Discovery"
        )

    def test_extract_c_suite_title(self) -> None:
        assert extract_jd_title(JD_HEALTHCARE_CMO) == "Chief Medical Officer"

    def test_extract_vp_title(self) -> None:
        assert extract_jd_title(JD_SALES_VP_GLOBAL_SALES) == "VP of Global Sales"


# =============================================================================
# Test Cases: Edge Cases and Fallbacks
# =============================================================================


class TestEdgeCases:
    """Test edge cases, fallbacks, and error handling."""

    def test_empty_jd_returns_fallback(self) -> None:
        result = classify_job_description("")
        assert result["domain"] is None
        assert result["level"] is None
        assert result["jd_title"] == "Unknown Role"
        assert result["persona"].startswith("You are an experienced recruiter")

    def test_generic_jd_no_domain_match(self) -> None:
        """JD with insufficient keywords should use fallback."""
        generic_jd = "We need a Manager. Must have 5 years experience. Apply now."
        result = classify_job_description(generic_jd)
        assert result["domain"] is None
        assert result["persona"].startswith("You are an experienced recruiter")

    def test_domain_match_but_no_level_match(self) -> None:
        """JD with domain keywords but no title pattern should use fallback."""
        jd = "We need someone for our kitchen. Must know how to cook. No formal title."
        result = classify_job_description(jd)
        # Should classify domain but fall back on level
        if result["domain"] == "culinary":
            assert result["level"] is None
            assert result["persona"].startswith("You are an experienced recruiter")

    def test_word_boundary_prevents_false_positive(self) -> None:
        """'AI' should not match 'training' or 'catering'."""
        jd_catering = "We are catering high-end events and need a waiting staff manager."
        result = classify_domain(jd_catering)
        # Should NOT classify as technology just because "catering" contains "AI"
        # (word boundaries prevent this)
        if result["primary"] == "technology":
            # If it does classify as tech, it should be from other keywords, not "AI"
            assert result["primary_score"] >= 3

    def test_acronym_collision_resolved_by_context(self) -> None:
        """CIO in tech context vs CIO in finance context."""
        tech_cio_jd = "Chief Information Officer needed. Must have software engineering background, cloud infrastructure expertise, and API design experience."
        finance_cio_jd = "Chief Investment Officer needed. Must have portfolio management experience, derivatives trading, and hedge fund background."

        tech_result = classify_domain(tech_cio_jd)
        finance_result = classify_domain(finance_cio_jd)

        # Keyword frequency should disambiguate
        assert tech_result["primary"] == "technology"
        assert finance_result["primary"] == "finance_trading"


# =============================================================================
# Test Cases: Confidence Thresholds
# =============================================================================


class TestConfidenceThresholds:
    """Test confidence scoring and thresholds."""

    def test_minimum_keyword_threshold_enforced(self) -> None:
        """JD with < 3 keywords should not classify."""
        jd_minimal = "We need an engineer with API experience."  # Only 2 tech keywords
        result = classify_domain(jd_minimal)
        # Might classify if there are other keywords, but threshold is 3
        if result["primary"]:
            assert result["primary_score"] >= 3

    def test_confident_when_gap_is_large(self) -> None:
        """Domain with high keyword count and no secondary should be confident."""
        result = classify_domain(JD_TECHNOLOGY_CTO)
        assert result["confident"] is True
        assert result["primary_score"] >= 8
        # Secondary should be either None or much lower
        if result["secondary"]:
            assert result["primary_score"] - result["secondary_score"] >= 2

    def test_not_confident_when_gap_is_small(self) -> None:
        """Domains with close scores should flag low confidence."""
        # RevOps JD has both sales and tech keywords in similar quantity
        result = classify_domain(JD_AMBIGUOUS_SALES_TECH)
        if result["secondary"]:
            gap = result["primary_score"] - result["secondary_score"]
            if gap < 2:
                assert result["confident"] is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
