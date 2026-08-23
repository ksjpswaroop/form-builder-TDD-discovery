from pathlib import Path
from typing import Optional

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

BASE_DIR = Path(__file__).resolve().parent.parent
SCHEMA_PATH = BASE_DIR / "app" / "schema" / "discovery_schema.yaml"
DATA_DIR = BASE_DIR / "data"
DOCUMENTS_DIR = DATA_DIR / "documents"
STATIC_DIR = BASE_DIR / "app" / "static"
TEMPLATES_DIR = BASE_DIR / "app" / "templates"

DEFAULT_SECRET_KEY = "change-me-in-production"
DEFAULT_ADMIN_PASSWORD = "admin"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = f"sqlite:///{DATA_DIR / 'sessions.db'}"
    ollama_host: str = "http://127.0.0.1:11434"
    ollama_model: str = "deepseek-v4-flash:cloud"
    max_questions_per_round: int = 8
    coverage_threshold: float = 0.75
    secret_key: str = DEFAULT_SECRET_KEY
    admin_username: str = "admin"
    admin_password: str = DEFAULT_ADMIN_PASSWORD
    admin_password_hash: Optional[str] = None
    app_base_url: str = "http://127.0.0.1:8000"
    environment: str = "development"
    root_path: str = ""
    rate_limit_login: str = "5/minute"
    rate_limit_retrieve: str = "10/minute"

    @property
    def is_production(self) -> bool:
        return self.environment.lower() == "production"

    @property
    def require_https(self) -> bool:
        return self.is_production


settings = Settings()
