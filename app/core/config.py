"""
Centralized application configuration.

Every tunable value (AWS region, model ID, simulation parameters, server
settings) lives here and is loaded from environment variables / a .env file.
This is the standard production pattern: nothing is hardcoded inside the
business logic, so the same code can run in dev, staging, or prod just by
swapping environment variables.
"""

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application-wide settings, loaded from environment variables or .env file."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ----- App metadata -----
    app_name: str = "SupplyChain Sentinel"
    app_env: str = "development"  # development | staging | production
    log_level: str = "INFO"

    # ----- API server -----
    api_host: str = "0.0.0.0"
    api_port: int = 8000

    # ----- AWS Bedrock -----
    # If aws_access_key_id / aws_secret_access_key are not set, the system
    # automatically falls back to a local MockLLM so the project is fully
    # runnable without any AWS account. This is a deliberate design choice
    # (see docs/ARCHITECTURE.md) so the agentic logic can be demoed offline.
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    bedrock_model_id: str = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    bedrock_max_tokens: int = 2048
    bedrock_temperature: float = 0.3
    use_mock_llm: bool = True  # forced True unless real creds are detected

    # ----- Simulation engine -----
    simulation_runs: int = 1000  # Monte Carlo iterations per stress test
    risk_escalation_threshold: float = 0.65  # 0-1 risk score that triggers re-simulation
    max_simulation_retries: int = 2

    # ----- Forecasting -----
    forecast_horizon_months: int = 12

    # ----- Report storage -----
    reports_dir: str = "data/reports"

    # ----- Sample data location -----
    # Where the Data Ingestion Agent reads suppliers.json/inventory.json from,
    # and where CSV uploads write back to. Configurable so tests can redirect
    # this to a temp directory instead of touching the real demo data.
    sample_data_dir: str = "data/sample"

    @property
    def bedrock_available(self) -> bool:
        """True only when real AWS credentials are present."""
        return bool(self.aws_access_key_id and self.aws_secret_access_key)


@lru_cache
def get_settings() -> Settings:
    """
    Cached settings accessor.

    Using lru_cache means Settings() is constructed only once per process
    (reading env vars / .env each time would be wasteful and could be
    inconsistent mid-run). Import get_settings() everywhere instead of
    instantiating Settings() directly.
    """
    return Settings()
