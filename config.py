import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
APP_ENV = os.getenv("APP_ENV", "development").strip().lower()
DATABASE_URL = os.getenv("DATABASE_URL")
SECRET_KEY = os.getenv("SECRET_KEY")


def normalize_database_url(database_url):
    if database_url and database_url.startswith("postgres://"):
        return "postgresql+psycopg://" + database_url[len("postgres://"):]
    if database_url and database_url.startswith("postgresql://"):
        return "postgresql+psycopg://" + database_url[len("postgresql://"):]
    return database_url


if not DATABASE_URL:
    if APP_ENV == "production":
        raise RuntimeError("DATABASE_URL must be configured in production.")
    DATABASE_URL = f"sqlite:///{BASE_DIR / 'studentvera_dev.db'}"
else:
    DATABASE_URL = normalize_database_url(DATABASE_URL)

if APP_ENV == "production" and (
    not SECRET_KEY or SECRET_KEY == "dev-secret-change-me" or len(SECRET_KEY) < 32
):
    raise RuntimeError("A strong SECRET_KEY must be configured in production.")


def _env_flag(name, default=False):
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}

class Config:
    SECRET_KEY = SECRET_KEY or "dev-secret-change-me"
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = APP_ENV == "production"
    LOGIN_DISABLED = False
    DEMO_MODE = _env_flag("DEMO_MODE")
    DEMO_ADMIN_PASSWORD = os.getenv("DEMO_ADMIN_PASSWORD")
    DEMO_OPERATOR_PASSWORD = os.getenv("DEMO_OPERATOR_PASSWORD")
    BOOTSTRAP_ADMIN_USERNAME = os.getenv("BOOTSTRAP_ADMIN_USERNAME")
    BOOTSTRAP_ADMIN_EMAIL = os.getenv("BOOTSTRAP_ADMIN_EMAIL")
    BOOTSTRAP_ADMIN_PASSWORD = os.getenv("BOOTSTRAP_ADMIN_PASSWORD")
    ADMIN_RESET_USERNAME = os.getenv("ADMIN_RESET_USERNAME")
    ADMIN_RESET_NEW_USERNAME = os.getenv("ADMIN_RESET_NEW_USERNAME")
    ADMIN_RESET_PASSWORD = os.getenv("ADMIN_RESET_PASSWORD")
    CONFIRM_ADMIN_PASSWORD_RESET = os.getenv("CONFIRM_ADMIN_PASSWORD_RESET")
    APP_NAME = os.getenv("APP_NAME", "STUDENTVERA AI")
    APP_ENV = APP_ENV

Config = Config
