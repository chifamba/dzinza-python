# backend/config.py
import os
from dotenv import load_dotenv
from datetime import timedelta
import redis

# --- Load Environment Variables ---
load_dotenv()

# --- Constants ---
DEFAULT_PAGE = 1
DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
# Tree visualization specific defaults
TREE_VIZ_DEFAULT_PAGE_SIZE = int(os.getenv("TREE_VIZ_PAGE_SIZE", "20"))
PAGINATION_DEFAULTS = {
    "page": DEFAULT_PAGE,
    "per_page": DEFAULT_PAGE_SIZE,
    "max_per_page": MAX_PAGE_SIZE,
    "tree_viz_per_page": TREE_VIZ_DEFAULT_PAGE_SIZE,
}

# --- Application Configuration ---
class Config:
    SECRET_KEY = os.getenv("FLASK_SECRET_KEY", "your_default_secret_key_for_session_signing")
    
    # Default pagination values
    DEFAULT_PAGE_SIZE = DEFAULT_PAGE_SIZE
    TREE_VIZ_DEFAULT_PAGE_SIZE = TREE_VIZ_DEFAULT_PAGE_SIZE
    
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
    REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")

    # Celery Configuration
    CELERY_BROKER_URL = os.getenv("CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", REDIS_URL)

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
    EMAIL_PORT = int(os.getenv("EMAIL_PORT", 587)) # Ensure int, provide default
    EMAIL_USE_TLS = os.getenv("EMAIL_USE_TLS", "true").lower() == "true"
    EMAIL_USERNAME = os.getenv("EMAIL_USER") # Typically same as MAIL_SENDER_EMAIL for auth
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")
    
    # MAIL_SENDER in the original config.py was defaulting to EMAIL_USERNAME.
    # The task asks for MAIL_SENDER_NAME and MAIL_SENDER_EMAIL explicitly.
    MAIL_SENDER_NAME = os.getenv('MAIL_SENDER_NAME', 'Dzinza Support')
    MAIL_SENDER_EMAIL = os.getenv('MAIL_SENDER_EMAIL', EMAIL_USERNAME) # Default to EMAIL_USERNAME if not set
    # APP_URL is requested by the task, FRONTEND_APP_URL serves this purpose. Using FRONTEND_APP_URL.

    # Debug and Environment
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = os.getenv('FLASK_DEBUG', 'false').lower() in ['true', '1', 't']
    SKIP_DB_INIT = os.getenv("SKIP_DB_INIT", "false").lower() == "true"
    FLASK_RUN_HOST = os.getenv('FLASK_RUN_HOST', '0.0.0.0')
    FLASK_RUN_PORT = int(os.getenv('FLASK_RUN_PORT', 8090))

    # Object Storage (S3/MinIO)
    OBJECT_STORAGE_TYPE = os.getenv("OBJECT_STORAGE_TYPE", "minio")
    OBJECT_STORAGE_ENDPOINT_URL = os.getenv("OBJECT_STORAGE_ENDPOINT_URL", "http://minio:9000")
    OBJECT_STORAGE_ACCESS_KEY = os.getenv("OBJECT_STORAGE_ACCESS_KEY", "minioadmin")
    OBJECT_STORAGE_SECRET_KEY = os.getenv("OBJECT_STORAGE_SECRET_KEY", "minioadmin")
    OBJECT_STORAGE_BUCKET_NAME = os.getenv("OBJECT_STORAGE_BUCKET_NAME", "family-tree-media")
    # Default OBJECT_STORAGE_SECURE to False if OBJECT_STORAGE_TYPE is 'minio', else True
    _object_storage_secure_default = "false" if OBJECT_STORAGE_TYPE == "minio" else "true"
    OBJECT_STORAGE_SECURE = os.getenv("OBJECT_STORAGE_SECURE", _object_storage_secure_default).lower() == "true"

    # Pagination Defaults
    PAGINATION_DEFAULTS = PAGINATION_DEFAULTS


# Instantiate config
config = Config()
