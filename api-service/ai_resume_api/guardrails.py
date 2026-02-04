"""Input and output guardrails for prompt injection defense.

This module provides:
- Input validation to detect prompt injection attempts
- Output filtering to prevent leakage of internal structures
- Logging of detected attacks for monitoring

Defense strategy follows OWASP LLM Top 10 recommendations.
"""

import re
from dataclasses import dataclass

import structlog

from ai_resume_api.observability import get_trace_id

logger = structlog.get_logger()

# =============================================================================
# Configuration
# =============================================================================

# Maximum number of suggested questions to include in guardrail response
MAX_SUGGESTED_QUESTIONS = 4


def _format_guardrail_response(
    profile_name: str | None = None,
    suggested_questions: list[str] | None = None,
) -> str:
    """Format a helpful guardrail response when injection is detected.

    Uses profile data to provide contextual suggested questions.

    Args:
        profile_name: Name of the candidate (e.g., "Jane")
        suggested_questions: List of suggested questions from profile

    Returns:
        Formatted response string that redirects user to legitimate questions.

    TODO: Add pronouns parameter when schema is updated to use correct pronouns
          (e.g., "she/her", "he/him", "they/them") for grammatically correct responses.
    """
    # Build the base response (pronoun-neutral phrasing for now)
    if profile_name:
        intro = f"I'm designed to help you learn if {profile_name} is a good fit for a role you're trying to fill."
    else:
        intro = "I'm designed to help you learn if this candidate is a good fit for a role you're trying to fill."

    response_parts = [intro]

    # Add suggested questions if available
    if suggested_questions and len(suggested_questions) > 0:
        response_parts.append("\nI can answer questions like:")
        # Take up to MAX_SUGGESTED_QUESTIONS
        questions_to_show = suggested_questions[:MAX_SUGGESTED_QUESTIONS]
        for question in questions_to_show:
            response_parts.append(f"• {question}")

    # Add closing encouragement (using "their" as pronoun-neutral)
    response_parts.append(
        "\nFeel free to ask about any aspect of their background or how they might fit "
        "a specific position. What would help with your evaluation?"
    )

    return "\n".join(response_parts)


# =============================================================================
# Input Guardrails - Detect Prompt Injection Attempts
# =============================================================================

# Patterns that indicate prompt injection attempts
# These are case-insensitive regex patterns
INJECTION_PATTERNS = [
    # Direct instruction override attempts
    r"ignore.*(?:previous|above|all|prior|earlier).*(?:instruction|directive|prompt|rule|command)",
    r"disregard.*(?:previous|above|all|prior|earlier).*(?:instruction|directive|prompt|rule)",
    r"forget.*(?:previous|above|all|prior|earlier).*(?:instruction|directive|prompt|rule)",
    # System prompt extraction attempts
    r"(?:reveal|show|display|output|print|echo|tell me).*(?:system|original|full|complete).*(?:prompt|instruction|directive|message)",
    r"(?:what|show).*(?:your|the).*(?:system|original|initial).*(?:prompt|instruction|message)",
    r"repeat.*(?:system|above|previous).*(?:prompt|instruction|message)",
    # Role/identity manipulation
    r"you are now",
    r"pretend (?:you are|to be)",
    r"act as (?:if|though)",
    r"roleplay as",
    r"switch to.*mode",
    r"enter.*mode",
    # Context/data extraction
    r"(?:show|reveal|output|dump).*(?:context|data|frame|chunk|raw|internal)",
    r"(?:what|show).*(?:context|data).*(?:provided|given|passed)",
    # Delimiter breaking attempts
    r"```.*(?:system|ignore|override)",
    r"</?(?:system|admin|root|sudo)>",
]

# Compile patterns for efficiency
_compiled_injection_patterns = [
    re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS
]


@dataclass
class InjectionDetectionResult:
    """Result of injection detection check."""

    is_injection: bool
    matched_pattern: str | None = None
    confidence: str = "low"  # low, medium, high


def detect_injection(text: str) -> InjectionDetectionResult:
    """Check if text contains prompt injection patterns.

    Args:
        text: User input text to check.

    Returns:
        InjectionDetectionResult with detection status and matched pattern.
    """
    text_normalized = " ".join(text.lower().split())  # Normalize whitespace

    for pattern in _compiled_injection_patterns:
        match = pattern.search(text_normalized)
        if match:
            # Log the detection with trace ID for correlation
            trace_id = get_trace_id()
            logger.warning(
                "injection_detected",
                trace_id=trace_id,
                pattern=pattern.pattern[:50],
                matched_text=match.group()[:100],
                input_preview=text[:100],
            )
            return InjectionDetectionResult(
                is_injection=True,
                matched_pattern=pattern.pattern,
                confidence="high" if "ignore" in match.group().lower() else "medium",
            )

    return InjectionDetectionResult(is_injection=False)


# =============================================================================
# Output Guardrails - Filter Internal Structure Leakage
# =============================================================================

# Patterns that indicate internal structure leakage in LLM output
OUTPUT_FILTER_PATTERNS = [
    # Frame/chunk references (the main issue we observed)
    r"\*\*Frame \d+\*\*",
    r"Frame \d+:",
    r"frame #?\d+",
    r"chunk #?\d+",
    # Context structure markers
    r"CONTEXT FROM RESUME:",
    r"---\s*\n.*(?:context|retrieved)",
    r"retrieved context:",
    # System prompt leakage markers
    r"CRITICAL SECURITY RULES:",
    r"INTERNAL STRUCTURE",
    r"System Message:",
    r"system prompt:",
]

# Compile patterns for efficiency
_compiled_output_patterns = [
    re.compile(pattern, re.IGNORECASE | re.MULTILINE) for pattern in OUTPUT_FILTER_PATTERNS
]


@dataclass
class OutputFilterResult:
    """Result of output filtering."""

    was_filtered: bool
    filtered_response: str
    matched_patterns: list[str]


def filter_output(response: str) -> OutputFilterResult:
    """Filter LLM response to remove internal structure leakage.

    Args:
        response: Raw LLM response text.

    Returns:
        OutputFilterResult with filtered text and detection info.
    """
    matched_patterns = []

    for pattern in _compiled_output_patterns:
        if pattern.search(response):
            matched_patterns.append(pattern.pattern)

    if matched_patterns:
        # Log the detection
        trace_id = get_trace_id()
        logger.warning(
            "output_filtered",
            trace_id=trace_id,
            patterns_matched=len(matched_patterns),
            response_preview=response[:200],
        )

        # Return a safe response instead
        filtered_response = (
            "I apologize, but I encountered an issue generating that response. "
            "Could you please rephrase your question about the candidate's qualifications?"
        )

        return OutputFilterResult(
            was_filtered=True,
            filtered_response=filtered_response,
            matched_patterns=matched_patterns,
        )

    return OutputFilterResult(
        was_filtered=False,
        filtered_response=response,
        matched_patterns=[],
    )


# =============================================================================
# Combined Guardrail Check
# =============================================================================


def check_input(
    text: str,
    profile_name: str | None = None,
    suggested_questions: list[str] | None = None,
) -> tuple[bool, str]:
    """Check user input and return (is_safe, response_if_blocked).

    Args:
        text: User input to check.
        profile_name: Optional candidate name for personalized response.
        suggested_questions: Optional list of suggested questions from profile.

    Returns:
        Tuple of (is_safe, message). If not safe, message contains the
        response to return to the user.
    """
    result = detect_injection(text)
    if result.is_injection:
        # Return helpful, personalized response instead of generic block
        response = _format_guardrail_response(profile_name, suggested_questions)
        return False, response
    return True, ""


def check_output(response: str) -> str:
    """Filter LLM output and return safe response.

    Args:
        response: Raw LLM response.

    Returns:
        Safe response (filtered if necessary).
    """
    result = filter_output(response)
    return result.filtered_response
