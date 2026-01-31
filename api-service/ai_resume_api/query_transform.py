"""Query transformation for optimal memvid retrieval.

This module implements query transformation strategies to bridge the gap
between natural language questions and how information is indexed in memvid.

V1 Strategy: Keyword Expansion
- Fast, single LLM call with small output
- Deterministic (same question -> same keywords)
- Debuggable (easy to inspect transformed queries)
"""

import structlog

logger = structlog.get_logger()


# Prompt template for keyword extraction
KEYWORD_EXTRACTION_PROMPT = """Extract 5-10 search keywords from this question.
Include the original key terms plus synonyms and related terms that would help find relevant resume content.
Output only keywords, space-separated, no punctuation.

Question: {question}
Keywords:"""


async def transform_query_keywords(
    question: str,
    openrouter_client,
) -> str:
    """
    Transform user question into retrieval-optimized keywords.

    Uses a fast LLM call to extract keywords that will match indexed content.
    Falls back to the original question if transformation fails.

    Args:
        question: The user's natural language question.
        openrouter_client: OpenRouter client for LLM calls.

    Returns:
        Space-separated keywords optimized for memvid search.
    """
    # Skip transformation if client not configured
    if not openrouter_client.is_configured:
        logger.debug("OpenRouter not configured, skipping query transformation")
        return question

    # Skip transformation for very short queries (likely already keywords)
    if len(question.split()) <= 3:
        logger.debug("Query too short for transformation", query=question)
        return question

    try:
        prompt = KEYWORD_EXTRACTION_PROMPT.format(question=question)

        # Use a simple non-streaming call for fast keyword extraction
        # We use minimal context since this is just keyword extraction
        response = await openrouter_client.chat(
            system_prompt="You are a search query optimizer. Extract keywords concisely.",
            context="",  # No context needed for keyword extraction
            user_message=prompt,
            history=None,
        )

        keywords = response.content.strip()

        # Validate output - should be space-separated words
        if keywords and len(keywords) < 500:  # Sanity check
            logger.info(
                "Query transformed",
                original=question[:50],
                keywords=keywords[:100],
                tokens_used=response.tokens_used,
            )
            return keywords
        else:
            logger.warning("Invalid keyword extraction output", output=keywords[:100])
            return question

    except Exception as e:
        logger.warning(
            "Query transformation failed, using original",
            error=str(e),
            question=question[:50],
        )
        return question


async def transform_query(
    question: str,
    openrouter_client,
    strategy: str = "keywords",
) -> str:
    """
    Transform user question for optimal retrieval.

    Args:
        question: The user's natural language question.
        openrouter_client: OpenRouter client for LLM calls.
        strategy: Transformation strategy ("keywords", "passthrough").

    Returns:
        Transformed query optimized for memvid search.
    """
    if strategy == "passthrough":
        return question
    elif strategy == "keywords":
        return await transform_query_keywords(question, openrouter_client)
    else:
        logger.warning(f"Unknown transform strategy: {strategy}, using passthrough")
        return question
