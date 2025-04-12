# src/db_utils.py

import os
import logging
from tinydb import TinyDB
from flask import g # Use Flask's application context global

# Define database paths relative to the project root or instance folder
DATA_DIR = os.path.join(os.path.dirname(__file__), '..', 'data') # Assumes db_utils.py is in src/
USERS_DB_PATH = os.path.join(DATA_DIR, 'users.tinydb')
TREE_DB_PATH = os.path.join(DATA_DIR, 'family_tree.tinydb')

def ensure_data_dir_exists():
    """Creates the data directory if it doesn't exist."""
    try:
        os.makedirs(DATA_DIR, exist_ok=True)
        logging.debug(f"Data directory ensured: {DATA_DIR}")
    except OSError as e:
        logging.error(f"Could not create data directory '{DATA_DIR}': {e}")
        raise # Re-raise the error to halt app startup if critical

def get_user_db():
    """
    Returns a TinyDB instance for the users database.
    Uses Flask's application context (g) to store the connection per request.
    """
    ensure_data_dir_exists() # Ensure directory exists before opening DB
    if 'user_db' not in g:
        logging.debug(f"Connecting to User DB: {USERS_DB_PATH}")
        g.user_db = TinyDB(USERS_DB_PATH)
    return g.user_db

def get_tree_db():
    """
    Returns a TinyDB instance for the family tree database.
    Uses Flask's application context (g) to store the connection per request.
    """
    ensure_data_dir_exists() # Ensure directory exists before opening DB
    if 'tree_db' not in g:
        logging.debug(f"Connecting to Tree DB: {TREE_DB_PATH}")
        g.tree_db = TinyDB(TREE_DB_PATH)
    return g.tree_db

def close_db(e=None):
    """Closes the database connections stored in Flask's application context."""
    user_db = g.pop('user_db', None)
    tree_db = g.pop('tree_db', None)

    if user_db is not None:
        logging.debug("Closing User DB connection.")
        user_db.close()
    if tree_db is not None:
        logging.debug("Closing Tree DB connection.")
        tree_db.close()

def init_app(app):
    """Register database functions with the Flask app."""
    app.teardown_appcontext(close_db)
    # You could add a CLI command here to initialize the DB if needed
    # app.cli.add_command(init_db_command)
