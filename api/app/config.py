from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    anthropic_api_key: str
    mongo_uri: str = "mongodb://localhost:27017/village_sim"
    enable_thinking: bool = False  # Enable extended thinking for Claude Opus 4.5
    
    class Config:
        env_file = ".env"
        case_sensitive = False
        extra = "ignore"  # Ignore extra fields from .env (like old API keys)


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()
