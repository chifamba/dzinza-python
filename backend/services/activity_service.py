# backend/services/activity_service.py
import uuid
import structlog
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError
from flask import abort # For aborting requests

from ..models import ActivityLog
from ..utils import paginate_query, _handle_sqlalchemy_error
from ..config import PAGINATION_DEFAULTS, DEFAULT_PAGE, DEFAULT_PAGE_SIZE
# from opentelemetry import trace # If specific tracing is needed here

# tracer = trace.get_tracer(__name__) # If specific tracing
logger = structlog.get_logger(__name__)

def get_activity_log_db(db: DBSession,
                        tree_id: Optional[uuid.UUID] = None,
                        user_id: Optional[uuid.UUID] = None,
                        page: int = DEFAULT_PAGE,
                        per_page: int = DEFAULT_PAGE_SIZE,
                        sort_by: str = "created_at",
                        sort_order: str = "desc"
                        ) -> Dict[str, Any]:
    """
    Fetches a paginated list of activity logs.
    Can be filtered by tree_id and/or user_id.
    """
    # with tracer.start_as_current_span("service.get_activity_log") as span: # Span in blueprint or higher level
    logger.info("Fetching activity logs", tree_id=tree_id, user_id=user_id, page=page, per_page=per_page)
    # if span:
    #     span.set_attributes({
    #         "tree.id": str(tree_id) if tree_id else "N/A",
    #         "user.id": str(user_id) if user_id else "N/A",
    #         "page": page, "per_page": per_page
    #     })
    try:
        query = db.query(ActivityLog)
        if tree_id:
            query = query.filter(ActivityLog.tree_id == tree_id)
        if user_id:
            query = query.filter(ActivityLog.user_id == user_id)
        
        # Ensure sort_by is a valid column for ActivityLog
        if not hasattr(ActivityLog, sort_by):
            logger.warning(f"Invalid sort_by column '{sort_by}' for ActivityLog. Defaulting to 'created_at'.")
            sort_by = "created_at"

        return paginate_query(query, ActivityLog, page, per_page, PAGINATION_DEFAULTS["max_per_page"], sort_by, sort_order)
    except SQLAlchemyError as e:
        logger.error("Database error fetching activity logs.", exc_info=True)
        _handle_sqlalchemy_error(e, "fetching activity logs", db) # This will abort
    except Exception as e:
        logger.error("Unexpected error fetching activity logs.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching activity logs.")
    return {} # Should be unreachable
