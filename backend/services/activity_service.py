# backend/services/activity_service.py
import uuid
import structlog
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError
from flask import abort

# Absolute imports for modules at the app root (/app)
from backend.models import ActivityLog
from backend.utils import paginate_query, _handle_sqlalchemy_error
from backend import config as app_config_module # To access PAGINATION_DEFAULTS

logger = structlog.get_logger(__name__)

def get_activity_log_db(db: DBSession,
                        tree_id: Optional[uuid.UUID] = None,
                        user_id: Optional[uuid.UUID] = None,
                        page: int = -1, # Default to trigger config lookup
                        per_page: int = -1,
                        sort_by: str = "created_at",
                        sort_order: str = "desc"
                        ) -> Dict[str, Any]:
    """Fetches a paginated list of activity logs."""
    cfg_pagination = app_config_module.config.PAGINATION_DEFAULTS
    if page == -1: page = cfg_pagination["page"]
    if per_page == -1: per_page = cfg_pagination["per_page"]

    logger.info("Fetching activity logs", tree_id=tree_id, user_id=user_id, page=page, per_page=per_page)
    try:
        query = db.query(ActivityLog)
        if tree_id: query = query.filter(ActivityLog.tree_id == tree_id)
        if user_id: query = query.filter(ActivityLog.user_id == user_id)
        
        if not hasattr(ActivityLog, sort_by):
            logger.warning(f"Invalid sort_by column '{sort_by}' for ActivityLog. Defaulting to 'created_at'.")
            sort_by = "created_at"

        return paginate_query(query, ActivityLog, page, per_page, cfg_pagination["max_per_page"], sort_by, sort_order)
    except SQLAlchemyError as e:
        logger.error("Database error fetching activity logs.", exc_info=True)
        _handle_sqlalchemy_error(e, "fetching activity logs", db)
    except Exception as e:
        logger.error("Unexpected error fetching activity logs.", exc_info=True)
        abort(500, description="An unexpected error occurred while fetching activity logs.")
    return {} 
