#!/usr/bin/env python3
"""
Integration tests using real OpenRouter API.

This test requires:
1. deployment/.env with OPENROUTER_API_KEY set
2. Optionally: running memvid service for full integration

Run with:
    cd api-service
    source .venv/bin/activate
    python tests/test_integration.py

Or run with pytest:
    cd api-service
    source .venv/bin/activate
    pytest tests/test_integration.py -v
"""

import asyncio
import os
import sys
from pathlib import Path

import pytest

# Load environment from deployment/.env
DEPLOYMENT_ENV = Path(__file__).parent.parent.parent / "deployment" / ".env"


def load_env_file(env_path: Path) -> dict[str, str]:
    """Load environment variables from .env file."""
    env_vars = {}
    if not env_path.exists():
        print(f"Warning: {env_path} not found")
        return env_vars

    with open(env_path) as f:
        for line in f:
            line = line.strip()
            # Skip comments and empty lines
            if not line or line.startswith("#"):
                continue
            # Handle export prefix
            if line.startswith("export "):
                line = line[7:]
            # Parse key=value
            if "=" in line:
                key, value = line.split("=", 1)
                env_vars[key.strip()] = value.strip()
    return env_vars


# Load and set environment variables before importing app modules
env_vars = load_env_file(DEPLOYMENT_ENV)
for key, value in env_vars.items():
    if key not in os.environ:  # Don't override existing env vars
        os.environ[key] = value

# Now import app modules (after env is set)
from ai_resume_api.config import get_settings
from ai_resume_api.openrouter_client import OpenRouterClient
from ai_resume_api.query_transform import transform_query


@pytest.mark.asyncio
async def test_openrouter_connection():
    """Test that we can connect to OpenRouter."""
    print("\n" + "=" * 60)
    print("TEST: OpenRouter Connection")
    print("=" * 60)

    settings = get_settings()
    # Mask API key in test output for security
    api_key_status = "CONFIGURED" if settings.openrouter_api_key else "NOT SET"
    print(f"API Key: {api_key_status}")
    print(f"Model: {settings.llm_model}")

    client = OpenRouterClient()
    await client.connect()

    if not client.is_configured:
        print("SKIP: OpenRouter not configured (no API key)")
        await client.close()
        return False

    print("OpenRouter client configured successfully")
    await client.close()
    return True


@pytest.mark.asyncio
async def test_query_transformation():
    """Test query transformation with real LLM."""
    print("\n" + "=" * 60)
    print("TEST: Query Transformation")
    print("=" * 60)

    client = OpenRouterClient()
    await client.connect()

    if not client.is_configured:
        print("SKIP: OpenRouter not configured")
        await client.close()
        return False

    test_questions = [
        "What programming languages does she know?",
        "Tell me about her security experience",
        "Would she be good for an early-stage startup?",
        "What are her biggest failures?",
    ]

    print("\nTransforming queries...\n")

    for question in test_questions:
        print(f"Q: {question}")
        try:
            transformed = await transform_query(
                question=question,
                openrouter_client=client,
                strategy="keywords",
            )
            print(f"   → {transformed}\n")
        except Exception as e:
            print(f"   ERROR: {e}\n")
            await client.close()
            return False

    await client.close()
    print("Query transformation test PASSED")
    return True


@pytest.mark.asyncio
async def test_chat_response():
    """Test full chat response (without memvid - uses mock context)."""
    print("\n" + "=" * 60)
    print("TEST: Chat Response (mock context)")
    print("=" * 60)

    client = OpenRouterClient()
    await client.connect()

    if not client.is_configured:
        print("SKIP: OpenRouter not configured")
        await client.close()
        return False

    # Mock context simulating memvid retrieval
    mock_context = """
**FAQ: What programming languages does she know?**
Jane's programming skills span infrastructure and data engineering:
- Python: 10+ years. Data pipelines, automation, ML tooling.
- Go: 5+ years. Microservices, CLI tools, Kubernetes operators.
- Bash: System scripting, CI/CD automation.
- Rust: Learning actively. Interested in systems programming.

**Skills: Programming Languages & Development**
Primary Languages: Python, Go, Bash
Infrastructure as Code: Terraform, Pulumi, Ansible
Limitations: Not a frontend developer, no mobile experience
"""

    settings = get_settings()
    question = "What programming languages does Jane know?"

    print(f"\nQuestion: {question}")
    print(f"Context length: {len(mock_context)} chars")
    print("\nGenerating response...\n")

    try:
        response = await client.chat(
            system_prompt=settings.system_prompt,
            context=mock_context,
            user_message=question,
            history=None,
        )
        print(f"Response ({response.tokens_used} tokens):")
        print("-" * 40)
        print(response.content)
        print("-" * 40)
    except Exception as e:
        print(f"ERROR: {e}")
        await client.close()
        return False

    await client.close()
    print("\nChat response test PASSED")
    return True


@pytest.mark.asyncio
async def test_streaming_response():
    """Test streaming chat response."""
    print("\n" + "=" * 60)
    print("TEST: Streaming Response")
    print("=" * 60)

    client = OpenRouterClient()
    await client.connect()

    if not client.is_configured:
        print("SKIP: OpenRouter not configured")
        await client.close()
        return False

    mock_context = """
**FAQ: What are her biggest failures?**
Jane believes talking about failures demonstrates self-awareness:

Failure 1: The Over-Engineered Platform (2023)
Built an internal platform so complex only she could maintain it.
Lesson: Now asks "can a new team member maintain this in 6 months?"

Failure 2: The Migration That Took 2x Longer (2021)
Underestimated legacy system complexity, skipped discovery phase.
Lesson: Now insists on 2-week discovery sprints before major migrations.
"""

    settings = get_settings()
    question = "What failures has Jane experienced?"

    print(f"\nQuestion: {question}")
    print("\nStreaming response:\n")
    print("-" * 40)

    try:
        full_response = ""
        async for chunk in client.chat_stream(
            system_prompt=settings.system_prompt,
            context=mock_context,
            user_message=question,
            history=None,
        ):
            if chunk.content:
                print(chunk.content, end="", flush=True)
                full_response += chunk.content
            if chunk.finish_reason:
                print(f"\n[finish: {chunk.finish_reason}, tokens: {chunk.tokens_used}]")
                break

        print("-" * 40)
    except Exception as e:
        print(f"\nERROR: {e}")
        await client.close()
        return False

    await client.close()
    print("\nStreaming response test PASSED")
    return True


async def main():
    """Run all integration tests."""
    print("=" * 60)
    print("AI Resume API - Integration Tests")
    print("=" * 60)
    print(f"Environment file: {DEPLOYMENT_ENV}")
    print(f"Environment loaded: {len(env_vars)} variables")

    results = []

    # Run tests
    results.append(("OpenRouter Connection", await test_openrouter_connection()))
    results.append(("Query Transformation", await test_query_transformation()))
    results.append(("Chat Response", await test_chat_response()))
    results.append(("Streaming Response", await test_streaming_response()))

    # Summary
    print("\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)

    passed = 0
    failed = 0
    skipped = 0

    for name, result in results:
        if result is True:
            status = "PASSED"
            passed += 1
        elif result is False:
            status = "FAILED"
            failed += 1
        else:
            status = "SKIPPED"
            skipped += 1
        print(f"  {name}: {status}")

    print(f"\nTotal: {passed} passed, {failed} failed, {skipped} skipped")

    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)
