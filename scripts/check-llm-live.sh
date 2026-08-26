#!/bin/bash
# End-to-end check that the configured LLM model actually answers.
#
# The catalogue check (validate_model / the `slow` pytest) confirms the model
# exists and has a healthy provider endpoint, and needs no credentials. It
# cannot tell you whether *your* key works, whether you are in quota, or
# whether the completion round-trip succeeds. This does, by driving a real
# request through the same OpenRouterClient the API uses -- so payload
# construction, streaming and error mapping are all exercised for real.
#
# Requires OPENROUTER_API_KEY. Costs one small completion.
#
# Usage:
#   OPENROUTER_API_KEY=sk-or-v1-... scripts/check-llm-live.sh
#   OPENROUTER_API_KEY=... LLM_MODEL=vendor/model:free scripts/check-llm-live.sh

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "${REPO_ROOT}/api-service"

if [[ -z "${OPENROUTER_API_KEY:-}" ]]; then
    echo "OPENROUTER_API_KEY is not set." >&2
    echo "" >&2
    echo "Run:  OPENROUTER_API_KEY=sk-or-v1-... scripts/check-llm-live.sh" >&2
    exit 2
fi

echo "=== LLM live check ==="
echo "model: ${LLM_MODEL:-<config default>}"
echo ""

MOCK_OPENROUTER=false uv run python - <<'PYTHON'
import asyncio
import sys

from ai_resume_api.config import get_settings
from ai_resume_api.openrouter_client import (
    OpenRouterClient,
    OpenRouterError,
    OpenRouterModelNotFoundError,
)


async def main() -> int:
    model = get_settings().llm_model
    client = OpenRouterClient(model=model)

    if not client.is_configured:
        print(f"FAIL: OPENROUTER_API_KEY is set but not in the expected format")
        return 1

    # 1. Catalogue + endpoint health (no credentials, no inference).
    available, detail = await client.validate_model()
    print(f"[1/3] availability : {'OK' if available else 'FAIL'} - {detail}")
    if not available:
        return 1

    # 2. Real non-streaming completion through the production client.
    try:
        response = await client.chat(
            system_prompt="You answer questions about a job candidate. Be brief.",
            context="The candidate is a platform engineer with Python and Kubernetes experience.",
            user_message="In one short sentence, what is the candidate's background?",
            max_tokens=64,
        )
    except OpenRouterModelNotFoundError as e:
        print(f"[2/3] completion   : FAIL - {e}")
        return 1
    except OpenRouterError as e:
        print(f"[2/3] completion   : FAIL - {type(e).__name__}: {e}")
        return 1
    finally:
        await client.close()

    if not (response.content or "").strip():
        print("[2/3] completion   : FAIL - model returned empty content")
        return 1
    preview = " ".join(response.content.split())[:110]
    print(f"[2/3] completion   : OK - {response.tokens_used} tokens")
    print(f"                     {preview}")

    # 3. Streaming, which the chat UI actually uses.
    client = OpenRouterClient(model=model)
    chunks = []
    try:
        async for chunk in client.chat_stream(
            system_prompt="You answer questions about a job candidate. Be brief.",
            context="The candidate is a platform engineer.",
            user_message="Name one skill in three words or fewer.",
        ):
            if chunk.content:
                chunks.append(chunk.content)
    except OpenRouterError as e:
        print(f"[3/3] streaming    : FAIL - {type(e).__name__}: {e}")
        return 1
    finally:
        await client.close()

    if not chunks:
        print("[3/3] streaming    : FAIL - no content chunks received")
        return 1
    print(f"[3/3] streaming    : OK - {len(chunks)} chunks")
    print(f"                     {' '.join(''.join(chunks).split())[:110]}")

    print("")
    print(f"All checks passed for '{model}'.")
    return 0


sys.exit(asyncio.run(main()))
PYTHON
