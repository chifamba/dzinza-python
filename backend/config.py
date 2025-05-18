# backend/config.py
import os
from dotenv import load_dotenv

"""
This file contains the application configuration loaded from environment variables.
"""
from datetime import timedelta
import redis

# --- Load Environment Variables ---
load_dotenv()

# --- Constants ---
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
PAGINATION_DEFAULTS = {
    "page": DEFAULT_PAGE,
    "per_page": DEFAULT_PAGE_SIZE,
    "max_per_page": MAX_PAGE_SIZE,
}

# --- Application Configuration ---
class Config:
    """
    Holds the configuration settings for the Flask application, including:
    - Database connection details
    - Redis connection details for session management and rate limiting
    - Flask session configuration
    - CORS origins
    - Rate limiting defaults
    - OpenTelemetry settings
    - Encryption key handling
    - Initial admin user credentials
    - Frontend URL
    - Email server configuration
    """
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "your_default_secret_key_for_session_signing")
    
    # Database
    DATABASE_URL = os.getenv('DATABASE_URL')
    if not DATABASE_URL:
        # This will be logged by the logger in database.py if it's still None there.
        # Raising an error here might be too early if config is imported by other modules
        # before the main app flow checks it.
        print("WARNING: DATABASE_URL environment variable is not set during config load.")
    DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", 20))
    DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", 10))
    DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", 1800))
    SQLALCHEMY_ECHO = os.getenv("SQLALCHEMY_ECHO", "False").lower() == "true"

    # Redis
    REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")

    # Session Configuration
    SESSION_TYPE = 'redis'
    SESSION_PERMANENT = False
    SESSION_USE_SIGNER = True
    SESSION_KEY_PREFIX = 'session:'
    SESSION_REDIS = redis.from_url(REDIS_URL) if REDIS_URL else None # Handle case where REDIS_URL might not be set
    SESSION_COOKIE_SECURE = os.getenv('FLASK_ENV', 'development') == 'production'
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = timedelta(days=7)

    # CORS
    CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:5173").split(',')

    # Rate Limiter
    RATELIMIT_STORAGE_URL = REDIS_URL
    RATELIMIT_DEFAULT = "100 per second;5000 per minute" 

    # OpenTelemetry
    OTEL_SERVICE_NAME = os.getenv("OTEL_SERVICE_NAME", "family-tree-backend")
    OTEL_EXPORTER_OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT")

    # Encryption
    ENCRYPTION_KEY_ENV_VAR = "ENCRYPTION_KEY"
    # Path relative to the 'backend' source directory (which becomes /app in container)
    ENCRYPTION_KEY_FILE_PATH_RELATIVE = os.path.join('data', 'encryption_key.json') 

    # Initial Admin User
    INITIAL_ADMIN_USERNAME = os.getenv("INITIAL_ADMIN_USERNAME", "admin")
    INITIAL_ADMIN_EMAIL = os.getenv("INITIAL_ADMIN_EMAIL", "admin@example.com")
    INITIAL_ADMIN_PASSWORD = os.getenv("INITIAL_ADMIN_PASSWORD")

    # Frontend URL
    FRONTEND_APP_URL = os.getenv("FRONTEND_APP_URL", "http://localhost:5173")
    
    # Email Configuration
    EMAIL_SERVER = os.getenv("EMAIL_SERVER")
    EMAIL_PORT = os.getenv("EMAIL_PORT")
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
    EMAIL_USERNAME = os.getenv("EMAIL_USER")
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    MAIL_SENDER = os.getenv("MAIL_SENDER", EMAIL_USERNAME)

    # Debug and Environment
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() in ['true', '1', 't']
    SKIP_DB_INIT = os.getenv("SKIP_DB_INIT", "false").lower() == "true"
    FLASK_RUN_HOST = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    FLASK_RUN_PORT = int(os.getenv('FLASK_RUN_PORT', 8090))

# Instantiate config
config = Config()
