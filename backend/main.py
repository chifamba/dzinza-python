# backend/main.py
import os
import uuid
import structlog
from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException # Ensure HTTPException is imported for error handler
from cryptography.fernet import Fernet

import config as app_config_module
# Import the database module itself to access its members directly after init
import database as db_module
import extensions as app_extensions_module
from utils import load_encryption_key

from blueprints.auth import auth_bp
from blueprints.trees import trees_bp
from blueprints.people import people_bp
from blueprints.relationships import relationships_bp
from blueprints.admin import admin_bp
from blueprints.health import health_bp

logger = structlog.get_logger(__name__)

def create_app(app_config_obj=app_config_module.config):
    """Application factory function."""
    app = Flask(__name__)
    app.config.from_object(app_config_obj)

    try:
        base_app_dir = os.path.dirname(os.path.abspath(__file__))
        key_file_path = os.path.join(base_app_dir, app_config_obj.ENCRYPTION_KEY_FILE_PATH_RELATIVE)
        
        logger.info("Attempting to load encryption key for Fernet.",
                    env_var=app_config_obj.ENCRYPTION_KEY_ENV_VAR,
                    file_path=key_file_path)
        
        encryption_key_bytes = load_encryption_key(
            env_var_name=app_config_obj.ENCRYPTION_KEY_ENV_VAR,
            file_path=key_file_path
        )

        if encryption_key_bytes:
            app_extensions_module.fernet_suite = Fernet(encryption_key_bytes)
            logger.info("Fernet initialized successfully for the application.")
        else:
            logger.critical("Encryption key is missing or load_encryption_key failed. Fernet NOT initialized. ENCRYPTION DISABLED.")
            app_extensions_module.fernet_suite = None
    except Exception as e:
        logger.critical(f"Failed to initialize Fernet for the app: {e}", exc_info=True)
        app_extensions_module.fernet_suite = None


    if not app_config_obj.SKIP_DB_INIT:
        try:
            db_module.initialize_database() # This calls init_engine and init_sessionlocal within database.py
            logger.info("Database initialized successfully by create_app.")
        except Exception as e:
            logger.critical(f"Application startup failed: Database initialization error.", error=str(e), exc_info=True)
            raise 
    else:
        logger.info("Skipping database initialization as per SKIP_DB_INIT.")
        # Ensure engine and SessionLocal are attempted if not skipping.
        if not db_module.engine: 
            try: db_module.init_engine() 
            except Exception as e: logger.critical(f"DB engine init failed when skipping full init: {e}", exc_info=True); raise
        if not db_module.SessionLocal: 
            try: db_module.init_sessionlocal()
            except Exception as e: logger.critical(f"DB SessionLocal init failed when skipping full init: {e}", exc_info=True); raise


    app_extensions_module.init_extensions(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(trees_bp)
    app.register_blueprint(people_bp)
    app.register_blueprint(relationships_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(health_bp)

    @app.before_request
    def before_request_hook():
        # Always get SessionLocal directly from the database module to ensure it's the initialized one
        if not db_module.SessionLocal: 
            logger.error("db_module.SessionLocal is not initialized. Cannot create DB session for request.")
            app.aborter(500, description="Database session factory not available.")
        g.db = db_module.SessionLocal() # Use the factory from the database module
        structlog.contextvars.bind_contextvars(
            request_id=str(uuid.uuid4()), path=request.path, method=request.method,
            remote_addr=request.remote_addr
        )

    @app.teardown_appcontext
    def teardown_db_hook(exception=None):
        db = g.pop('db', None)
        if db is not None:
            try:
                if exception: db.rollback(); logger.debug("DB session rolled back due to exception.", exc_info=exception)
            except Exception as e: logger.error("Error during DB session rollback.", error=str(e), exc_info=True)
            finally:
                try: db.close()
                except Exception as e: logger.error("Error closing DB session.", error=str(e), exc_info=True)
        structlog.contextvars.clear_contextvars()

    @app.errorhandler(Exception)
    def handle_global_exception(e):
        if not isinstance(e, HTTPException): # Check if it's already an HTTPException
            logger.error("Unhandled exception caught by global error handler.", exc_info=e, error_type=type(e).__name__)
        
        response_data = {"error": "Internal Server Error", "message": "An unexpected error occurred."}
        status_code = 500
        if isinstance(e, HTTPException):
            response_data["error"] = getattr(e, 'name', "Error")
            response_data["message"] = getattr(e, 'description', "An error occurred.")
            status_code = e.code or 500
            if isinstance(e.description, dict): 
                response_data["message"] = e.description.get("message", response_data["message"])
                if "details" in e.description: response_data["details"] = e.description["details"]
                if "code" in e.description: response_data["error_code"] = e.description["code"]
        
        return jsonify(response_data), status_code

    logger.info(f"Flask application '{app.name}' created and configured.")
    return app

if __name__ == '__main__':
    app_instance = create_app()
    logger.info("Starting Flask development server.",
                host=app_config_module.config.FLASK_RUN_HOST,
                port=app_config_module.config.FLASK_RUN_PORT,
                debug_mode=app_config_module.config.DEBUG)
    app_instance.run(host=app_config_module.config.FLASK_RUN_HOST,
                     port=app_config_module.config.FLASK_RUN_PORT,
                     debug=app_config_module.config.DEBUG)

app = create_app()
