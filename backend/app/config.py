from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import Optional


class Settings(BaseSettings):
    # App
    app_name: str = "Social Media Dashboard"
    debug: bool = False

    # Security
    secret_key: str = "change-this-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # Database
    database_url: str = "sqlite+aiosqlite:///./social_dashboard.db"

    # OpenAI
    openai_api_key: str = ""
    openai_model: str = "gpt-4o"
    dalle_model: str = "dall-e-3"

    # Twitter/X
    twitter_api_key: Optional[str] = None
    twitter_api_secret: Optional[str] = None
    twitter_access_token: Optional[str] = None
    twitter_access_token_secret: Optional[str] = None
    twitter_bearer_token: Optional[str] = None

    # LinkedIn
    linkedin_client_id: Optional[str] = None
    linkedin_client_secret: Optional[str] = None
    linkedin_access_token: Optional[str] = None

    # Facebook/Instagram
    facebook_app_id: Optional[str] = None
    facebook_app_secret: Optional[str] = None
    facebook_page_access_token: Optional[str] = None
    facebook_page_id: Optional[str] = None
    instagram_account_id: Optional[str] = None

    # CORS
    frontend_url: str = "http://localhost:5173"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
