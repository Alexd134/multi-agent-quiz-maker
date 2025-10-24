"""Application settings and configuration."""

from functools import lru_cache

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings

# Load .env file if present
load_dotenv()


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # AWS CONFIG
    aws_api_key_id: str = Field(
        ...,
        description="AWS API key ID",
        validation_alias="AWS_ACCESS_KEY_ID",
    )
    aws_api_key_secret: str = Field(
        ...,
        description="AWS API key",
        validation_alias="AWS_SECRET_ACCESS_KEY",
    )
    aws_default_region: str = Field(
        ...,
        description="AWS API region",
        validation_alias="AWS_DEFAULT_REGION",
    )

    # Model Configuration
    model_name: str = Field(
        default="anthropic.claude-3-7-sonnet-20250219-v1:0",
        description="Model to use (AWS Bedrock model ID)",
        validation_alias="MODEL_NAME",
    )

    # Generation Settings
    default_temperature: float = Field(
        default=0.8,  # higher temp than usual to try and generate more interesting questions
        ge=0.0,  # create max and min values for temp
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
    tavily_api_key: str | None = Field(
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
@lru_cache
def get_settings() -> Settings:
    """
    Get cached settings instance.

    Returns:
        Settings object with loaded configuration
    """
    return Settings()
