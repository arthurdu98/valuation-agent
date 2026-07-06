"""Configuration management module using pydantic-settings."""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic_settings.sources import YamlConfigSettingsSource


class Settings(BaseSettings):
    """Application settings loaded from environment variables and .env file."""

    # Database
    db_url: str = "postgresql://valuation:valuation_dev@localhost:5432/valuation"

    # LLM API Keys
    claude_api_key: str = ""
    deepseek_api_key: str = ""
    qwen_api_key: str = ""
    openai_api_key: str = ""

    # Data Source Credentials
    tushare_token: str = ""
    fred_api_key: str = ""

    # Data Source Toggles
    akshare_enabled: bool = True

    # Paths
    llm_config_path: str = "configs/llm.yaml"

    # Scheduling
    data_collection_interval_hours: int = 6

    # Development
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file="configs/settings.yaml",
        extra="ignore",
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls,
        init_settings,
        env_settings,
        dotenv_settings,
        file_secret_settings,
    ):
        """Load defaults from YAML, then allow env/.env to override them."""
        return (
            init_settings,
            env_settings,
            dotenv_settings,
            YamlConfigSettingsSource(settings_cls),
            file_secret_settings,
        )


settings = Settings()
