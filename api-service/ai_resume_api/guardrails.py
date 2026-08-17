"""Input and output guardrails for prompt injection defense.

This module provides:
- Input validation to detect prompt injection attempts
- Output filtering to prevent leakage of internal structures
- Logging of detected attacks for monitoring

Defense strategy follows OWASP LLM Top 10 recommendations.
"""

import base64
import binascii
import re
import unicodedata
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
    # Possessive-object override ("ignore your instructions"). The override
    # patterns above all require previous|above|all|prior|earlier between the
    # verb and the object, so this phrasing slipped through even once an
    # obfuscated payload was decoded.
    r"(?:ignore|disregard|forget|override)\s+(?:your|the|these|those|its|any)\s+"
    r"(?:instruction|directive|prompt|rule|command|guideline|constraint)",
]

# Compile patterns for efficiency
_compiled_injection_patterns = [
    re.compile(pattern, re.IGNORECASE) for pattern in INJECTION_PATTERNS
]


# =============================================================================
# Obfuscation normalization
# =============================================================================
#
# Pattern matching alone is defeated by trivial rewrites of the same payload.
# Rather than enumerate every variant as its own pattern, we derive a small set
# of normalized views of the input and match the existing patterns against each.
# A hit on any view is a hit.
#
# Each transform is deliberately narrow, because these run on recruiter-supplied
# text (including pasted job descriptions) where a false positive silently
# blocks a legitimate user.

# Homoglyphs that render as Latin letters but carry different codepoints.
# NFKC alone does not fold these -- Cyrillic 'о' (U+043E) is a distinct letter,
# not a compatibility variant of 'o'.
_CONFUSABLES = str.maketrans(
    {
        # Cyrillic
        "а": "a",
        "в": "b",
        "е": "e",
        "к": "k",
        "м": "m",
        "н": "h",
        "о": "o",
        "р": "p",
        "с": "c",
        "т": "t",
        "у": "y",
        "х": "x",
        "і": "i",
        "ѕ": "s",
        "ј": "j",
        "ԁ": "d",
        "ӏ": "l",
        "г": "r",
        # Greek
        "α": "a",
        "β": "b",
        "ε": "e",
        "ι": "i",
        "κ": "k",
        "ν": "v",
        "ο": "o",
        "ρ": "p",
        "τ": "t",
        "υ": "u",
        "χ": "x",
        "ѵ": "v",
    }
)

# Leetspeak digit/symbol substitutions.
_LEET = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "@": "a", "$": "s"}
)

# Runs of isolated single characters ("i g n o r e"). Requires at least four in
# a row so ordinary text ("a 5 x 3 grid", "CI / CD") is untouched.
_SPACED_CHARS_RE = re.compile(r"(?:(?<=\s)|^)(?:[a-z0-9]\s+){3,}[a-z0-9](?=\s|$)")

# Base64 candidates: long enough to carry a payload, and standard alphabet only.
_BASE64_CANDIDATE_RE = re.compile(r"[A-Za-z0-9+/]{16,}={0,2}")

# Upper bound on text we will normalize. Guards against a pathological input
# making every request pay for several full-text transforms.
MAX_NORMALIZE_CHARS = 8000


def _fold_confusables(text: str) -> str:
    """Fold Unicode look-alikes to their Latin equivalents."""
    return unicodedata.normalize("NFKC", text).translate(_CONFUSABLES)


def _fold_leet(text: str) -> str:
    """Fold common leetspeak substitutions to letters."""
    return text.translate(_LEET)


def _collapse_spaced_chars(text: str) -> str:
    """Collapse runs of space-separated single characters into words."""
    return _SPACED_CHARS_RE.sub(lambda m: re.sub(r"\s+", "", m.group()), text)


def _decode_base64_segments(text: str) -> str:
    """Return decoded text for any base64 segments that carry printable ASCII.

    Only segments that decode cleanly to mostly-printable ASCII are returned,
    so ordinary long tokens (hashes, IDs, digests) contribute nothing.
    """
    decoded_parts: list[str] = []
    for match in _BASE64_CANDIDATE_RE.finditer(text):
        segment = match.group()
        # Standard base64 needs length % 4 == 0; tolerate missing padding.
        padded = segment + "=" * (-len(segment) % 4)
        try:
            raw = base64.b64decode(padded, validate=True)
        except (binascii.Error, ValueError):
            continue
        try:
            candidate = raw.decode("utf-8")
        except UnicodeDecodeError:
            continue
        if not candidate:
            continue
        printable = sum(1 for ch in candidate if ch.isprintable() or ch.isspace())
        if printable / len(candidate) >= 0.9:
            decoded_parts.append(candidate)
    return " ".join(decoded_parts)


def _detection_views(text: str) -> list[tuple[str, str]]:
    """Build the set of normalized views to match patterns against.

    Returns a list of (view_name, text) pairs, always including the plain
    whitespace-normalized view first so ordinary inputs take the cheap path.
    """
    plain = " ".join(text.lower().split())
    views: list[tuple[str, str]] = [("plain", plain)]

    if len(plain) > MAX_NORMALIZE_CHARS:
        return views

    seen = {plain}

    def add(name: str, value: str) -> None:
        value = " ".join(value.split())
        if value and value not in seen:
            seen.add(value)
            views.append((name, value))

    folded = _fold_confusables(plain)
    add("confusables", folded)
    # Apply the remaining transforms on top of the folded text so a payload
    # combining techniques (leetspeak + homoglyphs) still reduces.
    add("leet", _fold_leet(folded))
    add("despaced", _collapse_spaced_chars(folded))
    add("leet+despaced", _collapse_spaced_chars(_fold_leet(folded)))

    decoded = _decode_base64_segments(text)
    if decoded:
        add("base64", " ".join(decoded.lower().split()))

    return views


@dataclass
class InjectionDetectionResult:
    """Result of injection detection check."""

    is_injection: bool
    matched_pattern: str | None = None
    confidence: str = "low"  # low, medium, high
    matched_view: str | None = None


def detect_injection(text: str) -> InjectionDetectionResult:
    """Check if text contains prompt injection patterns.

    Args:
        text: User input text to check.

    Returns:
        InjectionDetectionResult with detection status and matched pattern.
    """
    for view_name, view_text in _detection_views(text):
        for pattern in _compiled_injection_patterns:
            match = pattern.search(view_text)
            if not match:
                continue
            # Log the detection with trace ID for correlation
            trace_id = get_trace_id()
            logger.warning(
                "injection_detected",
                trace_id=trace_id,
                pattern=pattern.pattern[:50],
                matched_text=match.group()[:100],
                matched_view=view_name,
                input_preview=text[:100],
            )
            return InjectionDetectionResult(
                is_injection=True,
                matched_pattern=pattern.pattern,
                # A hit that only surfaces after de-obfuscation is stronger
                # evidence of intent than one in plain text, not weaker.
                confidence=(
                    "high"
                    if view_name != "plain" or "ignore" in match.group().lower()
                    else "medium"
                ),
                matched_view=view_name,
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
