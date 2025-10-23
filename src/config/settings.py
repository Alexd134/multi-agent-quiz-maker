"""Application settings and configuration."""

import os
from functools import lru_cache
from typing import Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env file if present
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # API Keys
    anthropic_api_key: str = Field(
        ...,
        description="Anthropic API key for Claude",
        validation_alias="ANTHROPIC_API_KEY",
    )

    # Model Configuration
    model_name: str = Field(
        default="claude-3-5-sonnet-20241022",
        description="Claude model to use",
        validation_alias="MODEL_NAME",
    )

    # Generation Settings
    default_temperature: float = Field(
        default=0.8, #higher temp than usual to try and generate more interesting questions
        ge=0.0, #create max and min values for temp
        le=1.0,
        description="Default temperature for question generation",
        validation_alias="DEFAULT_TEMPERATURE",
    )

    review_temperature: float = Field(
        default=0.3,
        ge=0.0,
        le=1.0,
        description="Temperature for quality review",
        validation_alias="REVIEW_TEMPERATURE",
    )

    validation_temperature: float = Field(
        default=0.1,
        ge=0.0,
        le=1.0,
        description="Temperature for answer validation",
        validation_alias="VALIDATION_TEMPERATURE",
    )

    # Quality Settings
    default_quality_threshold: float = Field(
        default=0.7,
        ge=0.0,
        le=1.0,
        description="Default quality threshold",
        validation_alias="QUALITY_THRESHOLD",
    )

    max_regeneration_attempts: int = Field(
        default=3,
        ge=0,
        le=10,
        description="Max regeneration attempts",
        validation_alias="MAX_REGENERATIONS",
    )

    # Output Settings
    default_output_path: str = Field(
        default="quiz",
        description="Default output file path",
        validation_alias="DEFAULT_OUTPUT",
    )

    # Optional: Web Search (for future feature)
    tavily_api_key: Optional[str] = Field(
        default=None,
        description="Tavily API key for web search (optional)",
        validation_alias="TAVILY_API_KEY",
    )

    use_web_search: bool = Field(
        default=False,
        description="Enable web search for better accuracy",
        validation_alias="USE_WEB_SEARCH",
    )

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
    }


# This is loaded the first time and then cached for further ues by other agents
@lru_cache()
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings object with loaded configuration
    """
    return Settings()