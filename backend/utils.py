# backend/utils.py
import re
import bcrypt
import time
import uuid
import os
import json
import structlog
from typing import Optional, Dict, Any, Tuple, TypeVar, Type
from sqlalchemy.orm import Query, Session as DBSession
from sqlalchemy import desc, asc, func
from werkzeug.exceptions import HTTPException
from flask import abort, request # For get_pagination_params
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy.exc import IntegrityError, NoResultFound, SQLAlchemyError

from .config import PAGINATION_DEFAULTS, MAX_PAGE_SIZE # Import pagination constants
# Assuming models.Base is accessible for TypeVar T, or define T more generically
# from .models import Base # This would create a circular dependency if utils is imported by models
# For TypeVar T, if it needs to be Base, utils cannot be imported by models.
# If T is just 'Any SQLAlchemy model', then it's fine.
from .extensions import db_operation_duration_histogram, get_fernet # For OTel metrics

logger = structlog.get_logger(__name__)
Base = object # Placeholder if models.Base cannot be imported due to circularity for TypeVar

T = TypeVar('T') # More generic TypeVar if Base cannot be imported

# --- Password Utilities ---
def _validate_password_complexity(password: str) -> None:
    """Validates password complexity requirements."""
    if len(password) < 8: raise ValueError("Password must be at least 8 characters long.")
    if not re.search(r'[A-Z]', password): raise ValueError("Password must contain at least one uppercase letter.")
    if not re.search(r'[a-z]', password): raise ValueError("Password must contain at least one lowercase letter.")
    if not re.search(r'[0-9]', password): raise ValueError("Password must contain at least one digit.")
    if not re.search(r'[!@#$%^&*()_+=\-[\]{};\':"\\|,.<>/?`~]', password): raise ValueError("Password must contain at least one special character.")

def _hash_password(password: str) -> str:
    """Hashes a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')

def _verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verifies a plain password against a hashed password."""
    if not plain_password or not hashed_password:
        return False
    try:
        return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))
    except Exception as e:
        logger.error("Error during password verification (checkpw)", exc_info=True, error=str(e))
        return False

# --- Pagination and Sorting Utilities ---
def apply_sorting(query: Query, model_cls: Type[T], sort_by: Optional[str], sort_order: Optional[str]) -> Query:
    """Applies sorting to a SQLAlchemy query."""
    if sort_by and hasattr(model_cls, sort_by):
        column_to_sort = getattr(model_cls, sort_by)
        if sort_order == "desc":
            query = query.order_by(desc(column_to_sort))
        else:
            query = query.order_by(asc(column_to_sort))
    elif not query._order_by_clauses: # Check if _order_by_clauses exists and is empty
        if hasattr(model_cls, "created_at"):
             query = query.order_by(desc(getattr(model_cls, "created_at")))
        elif hasattr(model_cls, "name"):
             query = query.order_by(asc(getattr(model_cls, "name")))
    return query

def paginate_query(
    query: Query,
    model_cls: Type[T],
    page: int,
    per_page: int,
    max_per_page: int = MAX_PAGE_SIZE, # Use constant from config
    sort_by: Optional[str] = None,
    sort_order: Optional[str] = "asc"
) -> Dict[str, Any]:
    """Paginates a SQLAlchemy query."""
    per_page = min(abs(per_page), max_per_page)
    page = abs(page) if page > 0 else 1 # Ensure page is at least 1

    query_for_sort_count = apply_sorting(query, model_cls, sort_by, sort_order)
    
    try:
        # Optimized count: remove order_by for counting if it doesn't affect the count result.
        # However, some complex queries with joins might need specific count approaches.
        count_query = query_for_sort_count.order_by(None) # Remove order_by for count
        total_items = count_query.count()
    except Exception as e:
        logger.warning(f"Efficient count failed, trying with entities: {e}", exc_info=False)
        # Fallback for more complex queries if .count() fails after order_by(None)
        # This might be slower or also fail depending on the query.
        try:
            total_items = query_for_sort_count.with_entities(func.count()).scalar()
        except Exception as count_err:
            logger.error(f"Count query failed for pagination: {count_err}", exc_info=True)
            abort(500, "Error counting items for pagination.")


    offset = (page - 1) * per_page
    # Re-apply sorting to the query that fetches items, if it was removed for count
    # The original query_for_sort_count already has sorting.
    items = query_for_sort_count.limit(per_page).offset(offset).all()

    total_pages = (total_items + per_page - 1) // per_page if total_items > 0 else 0

    return {
        "items": [item.to_dict() for item in items if hasattr(item, 'to_dict')],
        "page": page,
        "per_page": per_page,
        "total_items": total_items,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
        "sort_by": sort_by,
        "sort_order": sort_order
    }

def get_pagination_params() -> Tuple[int, int, Optional[str], Optional[str]]:
    """Extracts pagination and sorting parameters from request arguments."""
    page = request.args.get('page', default=PAGINATION_DEFAULTS["page"], type=int)
    per_page = request.args.get('per_page', default=PAGINATION_DEFAULTS["per_page"], type=int)
    sort_by = request.args.get('sort_by', default=None, type=str)
    sort_order = request.args.get('sort_order', default="asc", type=str)

    page = max(1, page)
    per_page = max(1, min(per_page, PAGINATION_DEFAULTS["max_per_page"]))
    if sort_order not in ["asc", "desc"]:
        sort_order = "asc"
    return page, per_page, sort_by, sort_order


# --- Database Utilities ---
def _handle_sqlalchemy_error(e: SQLAlchemyError, context: str, db: DBSession):
    """Handles SQLAlchemy errors by rolling back and aborting with appropriate HTTP status."""
    db.rollback()
    logger.error(f"SQLAlchemy Error during {context}", exc_info=True, error_type=type(e).__name__, orig_error=str(getattr(e, 'orig', None)))
    
    if isinstance(e, IntegrityError):
        detail = getattr(e.orig, 'diag', None)
        constraint_name = detail.constraint_name if detail else None
        error_message = str(e.orig).lower() if hasattr(e, 'orig') and e.orig is not None else str(e).lower()


        if constraint_name == 'users_username_key' or 'unique constraint "users_username_key"' in error_message:
            abort(409, description="Username already exists.")
        elif constraint_name == 'users_email_key' or 'unique constraint "users_email_key"' in error_message:
            abort(409, description="Email already exists.")
        elif constraint_name == 'tree_user_unique' or 'unique constraint "tree_user_unique"' in error_message:
             abort(409, description="User already has access to this tree.")
        elif 'foreign key constraint' in error_message:
             abort(409, description=f"Cannot complete action due to related data dependencies.")
        elif "not null constraint failed" in error_message or "null value in column" in error_message:
            column_match = re.search(r"column \"(.*?)\"", error_message)
            column_name = column_match.group(1) if column_match else "a required field"
            abort(400, description=f"Missing required field: {column_name}.")
        else:
            abort(409, description=f"Database conflict during {context}. Please check your input.")
    elif isinstance(e, NoResultFound):
        abort(404, description="The requested resource was not found.")
    else:
        abort(500, description=f"A database error occurred while {context}. Please try again later.")


def _get_or_404(db: DBSession, model_cls: Type[T], model_id: uuid.UUID, tree_id: Optional[uuid.UUID] = None) -> T:
    """Fetches a model instance by ID or aborts with 404 if not found."""
    # This span is better placed in the service layer that calls this utility.
    # For simplicity, keeping it here if this util is widely used directly by routes (though less ideal).
    # with tracer.start_as_current_span(f"db.get.{model_cls.__name__}") as span:
    #     span.set_attribute("db.system", "postgresql")
    #     span.set_attribute(f"{model_cls.__name__}.id", str(model_id))
    #     if tree_id: span.set_attribute("tree.id", str(tree_id))
        
    start_time = time.monotonic()
    obj = None
    try:
        query = db.query(model_cls)
        if tree_id and hasattr(model_cls, 'tree_id'):
             query = query.filter(model_cls.tree_id == tree_id) # type: ignore
        
        obj = query.filter(model_cls.id == model_id).one_or_none() # type: ignore
        
        duration = (time.monotonic() - start_time) * 1000
        if db_operation_duration_histogram: # Check if metric is initialized
            db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model_cls.__name__}", "db.status": "success" if obj else "not_found"})

        if obj is None:
            message = f"{model_cls.__name__} with ID {model_id} not found"
            if tree_id and hasattr(model_cls, 'tree_id'):
                message += f" in tree {tree_id}"
            logger.warning("Resource not found", model_name=model_cls.__name__, model_id=model_id, tree_id=tree_id)
            # if span: span.set_attribute("db.found", False)
            abort(404, description=message)
        
        # if span: span.set_attribute("db.found", True)
        return obj
    except SQLAlchemyError as e:
        duration = (time.monotonic() - start_time) * 1000
        if db_operation_duration_histogram:
            db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model_cls.__name__}", "db.status": "error"})
        # if span:
        #     span.record_exception(e)
        #     span.set_status(trace.Status(trace.StatusCode.ERROR, f"DB Error: {e}"))
        _handle_sqlalchemy_error(e, f"fetching {model_cls.__name__} ID {model_id}", db) # This will abort
    except HTTPException:
        raise
    except Exception as e:
        if 'start_time' in locals():
            duration = (time.monotonic() - start_time) * 1000
            if db_operation_duration_histogram:
                db_operation_duration_histogram.record(duration, {"db.operation": f"get.{model_cls.__name__}", "db.status": "error"})
        # if span:
        #     span.record_exception(e)
        #     span.set_status(trace.Status(trace.StatusCode.ERROR, "Non-DB Error during fetch"))
        logger.error(f"Unexpected error fetching {model_cls.__name__} ID {model_id}", exc_info=True)
        abort(500, "An unexpected error occurred while retrieving data.")
    return None # Should be unreachable due to aborts

# --- Encryption Utilities (Fernet related) ---
# The EncryptedString TypeDecorator is now in models.py for easier model definition.
# The Fernet suite instance itself should be managed by the app and passed around or accessed via app context/extensions.

# Example of how EncryptedString in models.py might get its Fernet instance:
# from .extensions import fernet_suite # If fernet_suite is initialized in extensions.py
# class MyModel(Base):
#     sensitive_field = Column(EncryptedString(fernet_instance=fernet_suite))

# Or, if EncryptedString uses a global from extensions:
# from .models import EncryptedString # Assuming EncryptedString internally calls get_fernet()
