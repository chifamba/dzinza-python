# backend/main.py
import os
import uuid
import structlog
from flask import Flask, g, jsonify, request
from werkzeug.exceptions import HTTPException
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
from blueprints.media import media_bp # Added import for media_bp

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


    # Initialize database: engine, session factory, tables, initial data
    # This will populate _thread_local.engine and _thread_local.session_factory for the main thread.
    # Worker threads will initialize their own on first access via get_engine()/get_session_factory().
    if not app_config_obj.SKIP_DB_INIT:
        try:
            db_module.initialize_database() 
            logger.info("Database initialized successfully by create_app.")
        except Exception as e:
            logger.critical(f"Application startup failed: Database initialization error.", error=str(e), exc_info=True)
            raise 
    else:
        logger.info("Skipping database initialization as per SKIP_DB_INIT.")
        # Still ensure engine and session factory are callable for the main thread
        # if full init is skipped, as they might be accessed by other parts of app setup.
        # get_engine() and get_session_factory() will handle initialization if not already done.
        db_module.get_engine()
        db_module.get_session_factory()


    app_extensions_module.init_extensions(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(trees_bp)
    app.register_blueprint(people_bp)
    app.register_blueprint(relationships_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(media_bp) # Registered media_bp

    @app.before_request
    def before_request_hook():
        # Get a thread-local session using the new get_db_session function
        g.db = db_module.get_db_session()
        structlog.contextvars.bind_contextvars(
            request_id=str(uuid.uuid4()), path=request.path, method=request.method,
            remote_addr=request.remote_addr
        )

    @app.teardown_appcontext
    def teardown_db_hook(exception=None):
        # g.db is the session instance from get_db_session()
        # For scoped_session, remove() is the standard way to return the session to the pool
        # and clear it from the current thread's scope.
        # The session itself (g.db) will be closed by scoped_session's management.
        session_factory = db_module.get_session_factory()
        if session_factory: # Ensure factory is available
            session_factory.remove()
            # logger.debug("DB session removed by scoped_session factory at teardown.") # Optional log
        
        # Clean up g.db to avoid potential leaks if remove() didn't clear it from g
        g.pop('db', None) 
        structlog.contextvars.clear_contextvars()


    @app.errorhandler(Exception)
    def handle_global_exception(e):
        if not isinstance(e, HTTPException): 
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
