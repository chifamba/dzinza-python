# backend/utils.py
import re
import bcrypt
import time
import uuid
import os
import json
import structlog
from typing import Optional, Dict, Any, Tuple, TypeVar, Type, List # Ensure List is imported
from sqlalchemy.orm import Query, Session as DBSession
from sqlalchemy import desc, asc, func
from werkzeug.exceptions import HTTPException
from flask import abort, request
from cryptography.fernet import Fernet, InvalidToken 
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError

# --- Encryption Key Loading (DEFINED VERY EARLY) ---
def load_encryption_key(env_var_name: str, file_path: str) -> Optional[bytes]:
    """
    Load encryption key from environment variable or file.
    Args:
        env_var_name: The name of the environment variable for the key.
        file_path: The absolute path to the JSON key file.
    Returns:
        The encryption key as bytes, or None if not found/error.
    """
    # Get a logger instance here, as this function might be called early.
    # It's better if logger is configured by the app first, but for robustness:
    _utils_logger = structlog.get_logger("backend.utils.load_encryption_key")

    key_str = os.getenv(env_var_name)
    if key_str:
        _utils_logger.info("Encryption key loaded from environment variable.", env_var=env_var_name)
        return key_str.encode('utf-8')

    _utils_logger.info("Attempting to load encryption key from file.", key_file_path=file_path)
    try:
        with open(file_path, 'r') as f:
            data = json.load(f)
            key_b64_str = data.get('key_b64')
            if key_b64_str:
                _utils_logger.info("Encryption key found in JSON file.", key_file_path=file_path)
                return key_b64_str.encode('utf-8')
            else:
                _utils_logger.error("Key 'key_b64' not found in JSON file.", key_file_path=file_path)
                return None
    except FileNotFoundError:
        _utils_logger.warning("Encryption key file not found.", key_file_path=file_path)
        return None
    except json.JSONDecodeError as e:
        _utils_logger.error("Failed to decode encryption key JSON file.", key_file_path=file_path, error=str(e))
        return None
    except Exception as e:
        _utils_logger.error("Unexpected error loading encryption key from file.", key_file_path=file_path, error=str(e), exc_info=True)
        return None

# Now import local project modules AFTER load_encryption_key is defined.
import config as app_config_module
import extensions # For db_operation_duration_histogram

# Initialize logger for the rest of the module.
logger = structlog.get_logger(__name__)


# --- Password Utilities ---
def _validate_password_complexity(password: str) -> None:
    if len(password) < 8: raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password): raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', password): raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r'[0-9]', password): raise ValueError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*()_+=\-[\]{};\':"\\|,.<>/?`~]', password): raise ValueError("Password must contain at least one special character.")

def _hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def _verify_password(plain_password: str, hashed_password: str) -> bool:
    if not plain_password or not hashed_password: return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error("Error during password verification (checkpw)", exc_info=True, error=str(e))
        return False

# --- Pagination and Sorting Utilities ---
def apply_sorting(query: Query, model_cls: Type[Any], sort_by: Optional[str], sort_order: Optional[str]) -> Query:
    if sort_by and hasattr(model_cls, sort_by):
        column_to_sort = getattr(model_cls, sort_by)
        if sort_order == "desc": query = query.order_by(desc(column_to_sort))
        else: query = query.order_by(asc(column_to_sort))
    elif not query._order_by_clauses: # type: ignore
        if hasattr(model_cls, "created_at"): query = query.order_by(desc(getattr(model_cls, "created_at")))
        elif hasattr(model_cls, "name"): query = query.order_by(asc(getattr(model_cls, "name")))
    return query

def paginate_query(
    query: Query, model_cls: Type[Any], page: int, per_page: int,
    max_per_page: int = -1, 
    sort_by: Optional[str] = None, sort_order: Optional[str] = "asc"
) -> Dict[str, Any]:
    if max_per_page == -1: # Use config if not overridden
        max_per_page = app_config_module.config.MAX_PAGE_SIZE

    per_page = min(abs(per_page), max_per_page)
    page = abs(page) if page > 0 else 1

    query_for_sort_count = apply_sorting(query, model_cls, sort_by, sort_order)
    
    total_items = 0
    try:
        # Detach order_by for counting, as it can be slow and is not needed for the count itself.
        count_query = query_for_sort_count.order_by(None) # type: ignore
        total_items = count_query.count()
    except Exception as e:
        logger.warning(f"Efficient count failed for {model_cls.__name__}, trying with entities: {e}", exc_info=False)
        try:
            # Fallback count method for more complex queries
            total_items = query_for_sort_count.with_entities(func.count()).scalar() # type: ignore
        except Exception as count_err:
            logger.error(f"Count query failed for pagination of {model_cls.__name__}: {count_err}", exc_info=True)
            abort(500, "Error counting items for pagination.")

    offset = (page - 1) * per_page
    items_raw = query_for_sort_count.limit(per_page).offset(offset).all()
    
    items_list: List[Dict[Any, Any]] = [] # Ensure items_list is always a list of dicts
    if items_raw:
        if hasattr(items_raw[0], 'to_dict') and callable(getattr(items_raw[0], 'to_dict')):
            items_list = [item.to_dict() for item in items_raw] # type: ignore
        else:
            logger.warning(f"Model {model_cls.__name__} instances do not have a to_dict method. Pagination items may be incomplete or incorrect.")
            # Attempting a generic conversion; this might not be suitable for all models.
            try:
                items_list = [vars(item) for item in items_raw]
                # Remove SQLAlchemy internal state if present
                for item_dict in items_list:
                    item_dict.pop('_sa_instance_state', None)
            except TypeError:
                 logger.error(f"Could not convert items of {model_cls.__name__} to dicts using vars().")
                 items_list = [] # Fallback to empty list if vars() fails

    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 0

    return {
        "items": items_list, "page": page, "per_page": per_page,
        "total_items": total_items, "total_pages": total_pages,
        "has_next": page < total_pages, "has_prev": page > 1,
        "sort_by": sort_by, "sort_order": sort_order
    }

def get_pagination_params() -> Tuple[int, int, Optional[str], Optional[str]]:
    # Access pagination defaults from the imported config module
    pagination_defaults = app_config_module.config.PAGINATION_DEFAULTS
    
    page_str = request.args.get('page', type=str) # Get as string to handle empty or invalid
    per_page_str = request.args.get('per_page', type=str)

    try:
        page = int(page_str) if page_str and page_str.isdigit() else pagination_defaults["page"]
    except (ValueError, TypeError):
        page = pagination_defaults["page"]
    
    try:
        per_page = int(per_page_str) if per_page_str and per_page_str.isdigit() else pagination_defaults["per_page"]
    except (ValueError, TypeError):
        per_page = pagination_defaults["per_page"]

    sort_by = request.args.get('sort_by', default=None, type=str)
    sort_order = request.args.get('sort_order', default="asc", type=str)

    page = max(1, page)
    per_page = max(1, min(per_page, pagination_defaults["max_per_page"]))
    if sort_order not in ["asc", "desc"]: sort_order = "asc"
    return page, per_page, sort_by, sort_order

# --- Database Utilities ---
def _handle_sqlalchemy_error(e: SQLAlchemyError, context: str, db: DBSession):
    db.rollback() # Ensure rollback happens first
    logger.error(f"SQLAlchemy Error: {context}", exc_info=True, error_type=type(e).__name__, orig_error=str(getattr(e, 'orig', None)))
    
    if isinstance(e, IntegrityError):
        detail = getattr(e.orig, 'diag', None) # For psycopg2, might differ for other DBs
        constraint_name = detail.constraint_name if detail else None
        error_message = str(e.orig).lower() if hasattr(e, 'orig') and e.orig is not None else str(e).lower()

        if constraint_name == 'users_username_key' or 'unique constraint "users_username_key"' in error_message:
            abort(409, description="Username already exists.")
        elif constraint_name == 'users_email_key' or 'unique constraint "users_email_key"' in error_message:
            abort(409, description="Email already exists.")
        elif constraint_name == 'tree_user_unique' or 'unique constraint "tree_user_unique"' in error_message:
             abort(409, description="User already has access to this tree.")
        elif 'foreign key constraint' in error_message:
             # Try to provide a more generic but helpful message if specific parsing is hard
             abort(409, description=f"Cannot complete action due to a data dependency conflict in '{context}'.")
        elif "not null constraint failed" in error_message or "null value in column" in error_message:
            column_match = re.search(r"column \"(.*?)\"", error_message) # DB specific parsing
            column_name = column_match.group(1) if column_match else "a required field"
            abort(400, description=f"Missing required field: {column_name} for '{context}'.")
        else:
            abort(409, description=f"A database conflict occurred while {context}. Please check your input.")
    elif isinstance(e, NoResultFound):
        abort(404, description=f"The requested resource for '{context}' was not found.")
    else: # Catch-all for other SQLAlchemyErrors
        abort(500, description=f"A database error occurred while {context}. Please try again later.")


def _get_or_404(db: DBSession, model_cls: Type[Any], model_id: uuid.UUID, tree_id: Optional[uuid.UUID] = None) -> Any:
    start_time = time.monotonic()
    obj = None
    try:
        query = db.query(model_cls)
        if tree_id and hasattr(model_cls, 'tree_id'):
             query = query.filter(getattr(model_cls, 'tree_id') == tree_id)
        
        obj = query.filter(getattr(model_cls, 'id') == model_id).one_or_none()
        
        duration = (time.monotonic() - start_time) * 1000
        if extensions.db_operation_duration_histogram: # Check if metric is initialized
            extensions.db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model_cls.__name__}", "db.status": "success" if obj else "not_found"})

        if obj is None:
            message = f"{model_cls.__name__} with ID {model_id} not found"
            if tree_id and hasattr(model_cls, 'tree_id'): message += f" in tree {tree_id}"
            logger.warning("Resource not found by _get_or_404", model_name=model_cls.__name__, model_id=model_id, tree_id=tree_id)
            abort(404, description=message)
        
        return obj
    except SQLAlchemyError as e: # Catch SQLAlchemy errors specifically
        duration = (time.monotonic() - start_time) # type: ignore
        if extensions.db_operation_duration_histogram:
            extensions.db_operation_duration_histogram.record(duration * 1000, {"db.operation": f"get.{model_cls.__name__}", "db.status": "error"})
        _handle_sqlalchemy_error(e, f"fetching {model_cls.__name__} ID {model_id}", db) # This will abort
    except HTTPException: # Re-raise HTTPExceptions (like abort(404))
        raise
    except Exception as e: # Catch any other unexpected errors
        if 'start_time' in locals(): # type: ignore
            duration = (time.monotonic() - start_time) * 1000 # type: ignore
            if extensions.db_operation_duration_histogram:
                extensions.db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model_cls.__name__}", "db.status": "error"})
        logger.error(f"Unexpected error in _get_or_404 for {model_cls.__name__} ID {model_id}", exc_info=True)
        abort(500, "An unexpected error occurred while retrieving data.")
    # This line should ideally not be reached if aborts are raised correctly.
    # Adding a type hint that matches the expected return type if obj is found.
    return None # Should be unreachable if aborts occur
