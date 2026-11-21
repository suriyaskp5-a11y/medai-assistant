from pydantic_settings import BaseSettings
from pydantic import model_validator
from typing import Any


class Settings(BaseSettings):
    gemini_api_key: str
    firebase_service_account_json: str
    allowed_origins: str = "*"
    max_requests_per_minute: int = 5
    max_requests_per_day: int = 25
    max_input_chars: int = 2000

    model_config = {"env_file": ".env", "case_sensitive": False}


settings = Settings()
