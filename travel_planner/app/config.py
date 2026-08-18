from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    openai_api_key: Optional[str] = None
    groq_api_key: Optional[str] = None
    default_llm_provider: str = "openai"
    tavily_api_key: Optional[str] = None
    serper_api_key: Optional[str] = None
    exa_api_key: Optional[str] = None
    host: str = "127.0.0.1"
    port: int = 8000

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

settings = Settings()
