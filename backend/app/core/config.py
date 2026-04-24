import os
from pathlib import Path

from dotenv import load_dotenv


BACKEND_DIR = Path(__file__).resolve().parents[2]
PROJECT_DIR = BACKEND_DIR.parent
DEFAULT_DATABASE_URL = f"sqlite:///{(BACKEND_DIR / 'dwplus.db').as_posix()}"

load_dotenv(PROJECT_DIR / ".env")
load_dotenv(BACKEND_DIR / ".env", override=True)


class Settings:
    """Small settings object to keep the first prototype dependency-light."""

    app_name: str = os.getenv("APP_NAME", "DWPLUS Ticket Triage API")
    app_env: str = os.getenv("APP_ENV", "development")
    jira_email: str | None = os.getenv("JIRA_EMAIL") or None
    jira_api_token: str | None = os.getenv("JIRA_API_TOKEN") or None
    jira_url: str = os.getenv("JIRA_URL", "https://dwplus.atlassian.net")
    database_url: str = os.getenv("DATABASE_URL") or DEFAULT_DATABASE_URL


settings = Settings()
