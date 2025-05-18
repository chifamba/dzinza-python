# backend/main.py (or app.py)
import os
import structlog
from flask import Flask, g, jsonify
from werkzeug.exceptions import HTTPException
from cryptography.fernet import Fernet # For Fernet initialization

# Import configurations and initializers
from .config import config
from .database import initialize_database, SessionLocal, engine as db_engine # Import engine
from .extensions import init_extensions, fernet_suite as global_fernet_suite, logging_instrumentor
from .utils import load_encryption_key # For initializing Fernet

# Import blueprints
from .blueprints.auth import auth_bp
from .blueprints.trees import trees_bp
from .blueprints.people import people_bp
from .blueprints.relationships import relationships_bp
from .blueprints.admin import admin_bp
from .blueprints.health import health_bp

logger = structlog.get_logger(__name__)

def create_app(app_config_obj=config):
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(app_config_obj)

    # Initialize Fernet for encryption
    # This needs to happen before EncryptedString type in models might be used with it.
    # Assign to the global_fernet_suite in extensions.py
    try:
        encryption_key_bytes = load_encryption_key() # Uses config for paths/env vars
        if encryption_key_bytes:
            # This is a bit of a hack to set the global. Better to pass it around.
            from . import extensions 
            extensions.fernet_suite = Fernet(encryption_key_bytes)
            logger.info("Fernet initialized successfully for the application.")
        else:
            logger.critical("Encryption key is missing. Fernet cannot be initialized for the app.")
            # Decide if app should run without encryption or raise error
            # For now, it will run, but EncryptedString will fallback or fail.
    except Exception as e:
        logger.critical(f"Failed to initialize Fernet for the app: {e}", exc_info=True)
        # Decide on fallback or error


    # Initialize database (engine, session factory, tables, initial data)
    # This will set up database.engine and database.SessionLocal
    if not app_config_obj.SKIP_DB_INIT:
        try:
            initialize_database() # This function now calls init_engine and init_sessionlocal internally
            logger.info("Database initialized successfully by create_app.")
        except Exception as e:
            logger.critical(f"Application startup failed during database initialization: {e}", exc_info=True)
            raise # Prevent app from starting if DB init fails
    else:
        logger.info("Skipping database initialization as per SKIP_DB_INIT environment variable.")
        # Ensure engine and SessionLocal are at least attempted if not skipping
        if not db_engine:
            from .database import init_engine
            init_engine()
        if not SessionLocal:
            from .database import init_sessionlocal
            init_sessionlocal()


    # Initialize Flask extensions
    init_extensions(app) # This now also initializes OpenTelemetry

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(trees_bp)
    app.register_blueprint(people_bp)
    app.register_blueprint(relationships_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(health_bp)

    # --- Request Lifecycle Hooks ---
    @app.before_request
    def before_request_hook():
        if not SessionLocal:
            logger.error("SessionLocal is not initialized. Cannot create DB session for request.")
            abort(500, "Database session factory not available.")
        g.db = SessionLocal()
        # Bind contextvars for structlog if not handled by OTel logging
        structlog.contextvars.bind_contextvars(
            request_id=str(uuid.uuid4()),
            path=request.path,
            method=request.method,
            remote_addr=request.remote_addr
        )


    @app.teardown_appcontext
    def teardown_db_hook(exception=None):
        db = g.pop('db', None)
        if db is not None:
            try:
                if exception:
                    db.rollback()
                    logger.debug("Rolled back DB session due to exception in request.", exc_info=exception)
                # else:
                #    db.commit() # Commits should be explicit in service layers
            except Exception as e:
                logger.error(f"Error during DB session teardown (rollback/commit): {e}", exc_info=True)
            finally:
                try:
                    db.close()
                except Exception e:
                    logger.error(f"Error closing database session: {e}", exc_info=True)
        structlog.contextvars.clear_contextvars()


    # --- Global Error Handler ---
    @app.errorhandler(Exception)
    def handle_global_exception(e):
        if not isinstance(e, HTTPException):
            logger.error(
                "Unhandled exception caught", exc_info=e, error_type=type(e).__name__
            )
        
        if isinstance(e, HTTPException):
            response_data = {
                "error": getattr(e, 'name', "Error"),
                "message": getattr(e, 'description', "An error occurred."),
            }
            if isinstance(e.description, dict): # If abort used a dict for description
                response_data["message"] = e.description.get("message", response_data["message"])
                if "details" in e.description: response_data["details"] = e.description["details"]
                if "code" in e.description: response_data["error_code"] = e.description["code"]
            
            response = jsonify(response_data)
            response.status_code = e.code or 500
            return response

        return jsonify({
            "error": "Internal Server Error",
            "message": "An unexpected error occurred. Please try again later."
        }), 500

    logger.info(f"Flask application '{app.name}' created successfully.")
    return app

# --- Main execution ---
# This part is usually for running with `python main.py`
# In production, a WSGI server like Gunicorn will import `app` from `create_app()`.
if __name__ == '__main__':
    # Create the app instance using the factory
    app_instance = create_app()
    
    # Configure logging for when running directly (if not already handled by OTel/Structlog setup)
    # Basic logging config is done in config.py or extensions.py for structlog
    
    logger.info(
        "Starting Flask development server",
        host=config.FLASK_RUN_HOST,
        port=config.FLASK_RUN_PORT,
        debug_mode=config.DEBUG
    )
    app_instance.run(
        host=config.FLASK_RUN_HOST,
        port=config.FLASK_RUN_PORT,
        debug=config.DEBUG
    )

# For Gunicorn or other WSGI servers, they would typically look for an `app` variable.
# So, we can assign the created app to a variable named `app` at the module level.
app = create_app()

