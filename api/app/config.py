from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    mongo_db_uri: str = "mongodb://localhost:27017/ai_life_sim"
    database_name: str = "ai_life_sim"
    
    # Optional API keys for future LLM integration
    cerebras_api_key: Optional[str] = None
    anthropic_api_key: Optional[str] = None
    gemini_api_key: Optional[str] = None
    openai_api_key: Optional[str] = None
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"  # Ignore any extra fields in .env
    )


settings = Settings()

