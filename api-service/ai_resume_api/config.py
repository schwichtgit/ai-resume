"""Environment configuration using pydantic-settings."""

import json
from functools import lru_cache
from pathlib import Path
from typing import Literal, Optional

import structlog
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = structlog.get_logger()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # Mock control (opt-in feature gates for testing)
    mock_memvid_client: bool = False  # Use mock gRPC client (don't connect to memvid service)
    mock_openrouter: bool = False  # Use mock LLM responses (don't call OpenRouter API)

    # OpenRouter configuration
    openrouter_api_key: str = ""
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "nvidia/nemotron-nano-2407-instruct"
    llm_max_tokens: int = 1024
    llm_temperature: float = 0.7

    # Memvid gRPC service
    memvid_grpc_host: str = "localhost"
    memvid_grpc_port: int = 50051
    memvid_timeout_seconds: float = 5.0

    # Session management
    session_ttl: int = 1800  # 30 minutes
    max_sessions: int = 1000
    max_history_messages: int = 20

    # Rate limiting
    rate_limit_per_minute: int = 10

    # Server configuration
    port: int = 3000
    host: str = "0.0.0.0"
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = "INFO"
    environment: Literal["development", "production"] = "development"

    # Profile data path
    profile_json_path: str = "data/.memvid/profile.json"

    # System prompt for the LLM (fallback if profile.json not found)
    system_prompt: str = """You are an AI assistant representing a job candidate. Your role is to answer questions about their professional background, skills, and experience based on the context provided.

Guidelines:
- Only answer based on the provided context from the resume
- Be honest and accurate - don't make up information
- If you don't have information to answer a question, say so
- Be professional but personable
- Highlight relevant achievements and skills when appropriate
- Keep responses concise but informative"""

    @property
    def is_development(self) -> bool:
        """Check if running in development mode."""
        return self.environment == "development"

    @property
    def has_openrouter_key(self) -> bool:
        """Check if OpenRouter API key is configured."""
        return bool(self.openrouter_api_key and self.openrouter_api_key.startswith("sk-"))

    def validate_openrouter_api_key(self) -> int:
        """Validate OpenRouter API key format.

        Returns:
            Integer status code (not derived from key content):
            - 0: not set
            - 1: valid format
            - 2: incorrect prefix
            - 3: incorrect length
            - 4: invalid characters
        """
        if not self.openrouter_api_key:
            return 0

        key = self.openrouter_api_key

        # Check prefix
        if not key.startswith("sk-or-v1-"):
            return 2

        # Check length
        if len(key) < 40 or len(key) > 100:
            return 3

        # Check character set
        import re

        key_body = key[10:]  # After "sk-or-v1-"
        if not re.match(r"^[A-Za-z0-9_-]+$", key_body):
            return 4

        return 1

    @property
    def memvid_grpc_url(self) -> str:
        """Construct memvid gRPC URL from host and port.

        Priority:
        1. MEMVID_GRPC_URL env var (explicit override)
        2. MEMVID_GRPC_HOST:MEMVID_GRPC_PORT (from config)
        3. localhost:50051 (hardcoded fallback for development)
        """
        import os

        # Check for explicit URL override
        if explicit_url := os.getenv("MEMVID_GRPC_URL"):
            return explicit_url

        # Use host:port from config (supports container service names)
        return f"{self.memvid_grpc_host}:{self.memvid_grpc_port}"

    async def load_profile_from_memvid(self) -> Optional[dict]:
        """Load profile data from memvid using memory card state() lookup.

        Profile is stored as a memory card during ingest, providing O(1) retrieval
        without the text truncation issues of search results.

        Returns:
            Profile dict if found, None otherwise.
        """
        from ai_resume_api.memvid_client import get_memvid_client

        try:
            client = await get_memvid_client()

            # Use get_state() for O(1) memory card lookup
            # Profile stored with entity="__profile__", slot="data"
            state = await client.get_state("__profile__")

            if not state or not state.get("found"):
                logger.warning("Profile memory card '__profile__' not found in memvid")
                return None

            # Get the profile JSON from the "data" slot
            slots = state.get("slots", {})
            profile_json = slots.get("data")

            if not profile_json:
                logger.error("Profile memory card found but 'data' slot is empty")
                return None

            # Parse and return the profile
            profile = json.loads(profile_json)
            logger.info("Profile loaded successfully from memvid memory card")
            return profile

        except json.JSONDecodeError as e:
            logger.error("Failed to parse profile JSON from memvid", error=str(e))
            return None
        except Exception as e:
            logger.error("Failed to load profile from memvid", error=str(e))
            return None

    def load_profile(self) -> Optional[dict]:
        """Load profile data (deprecated - use async version).

        This method is deprecated. Use load_profile_from_memvid() instead.
        For backward compatibility, falls back to profile.json if it exists.

        Returns:
            Profile dict if file exists, None otherwise.
        """
        profile_path = Path(self.profile_json_path)
        if not profile_path.exists():
            return None

        try:
            with open(profile_path) as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return None

    def get_system_prompt_from_profile(self) -> str:
        """Get system prompt from profile with ground facts injection."""
        profile = self.load_profile()
        system_prompt = profile.get("system_prompt") if profile else self.system_prompt

        # Inject ground facts to prevent hallucination
        if profile:
            # Add ground facts preamble if not already present
            if "GROUND FACTS" not in system_prompt:
                candidate_name = profile.get("name", "this candidate")
                title = profile.get("title", "")

                # Build ground facts list
                facts = [f"This resume is about: {candidate_name}"]
                if title:
                    facts.append(f"Current/Target Role: {title}")

                # Add company names from experience
                experiences = profile.get("experience", [])
                if experiences and len(experiences) > 0:
                    companies = [
                        exp.get("company") for exp in experiences[:3] if exp.get("company")
                    ]
                    if companies:
                        facts.append(f"Key Companies: {', '.join(companies)}")

                facts_text = "\n  ".join(f"- {fact}" for fact in facts)
                ground_facts = f"""
GROUND FACTS (NEVER VIOLATE THESE):
  {facts_text}
  - If a question asks about a different person, respond:
    "This resume is for {candidate_name}, not [other name]. Please ask about {candidate_name}'s qualifications."
  - NEVER answer questions about people, companies, or experiences not mentioned in the context

"""
                # Insert ground facts after the first line
                lines = system_prompt.split("\n", 1)
                if len(lines) == 2:
                    system_prompt = lines[0] + "\n" + ground_facts + lines[1]
                else:
                    system_prompt = ground_facts + system_prompt

        return system_prompt


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
