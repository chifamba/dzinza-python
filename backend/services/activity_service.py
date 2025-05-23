# backend/services/activity_service.py
import uuid
import structlog
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session as DBSession
from sqlalchemy.exc import SQLAlchemyError
from flask import abort

# Absolute imports for modules at the app root (/app)
from models import ActivityLog
from utils import paginate_query, _handle_sqlalchemy_error
import config as app_config_module # To access PAGINATION_DEFAULTS

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


def log_activity(db: DBSession,
                 action_type: str,
                 entity_type: str,
                 entity_id: Optional[uuid.UUID],
                 actor_user_id: Optional[uuid.UUID] = None, # Renamed from user_id to avoid confusion with entity's user_id
                 tree_id: Optional[uuid.UUID] = None,
                 previous_state: Optional[Dict[str, Any]] = None,
                 new_state: Optional[Dict[str, Any]] = None,
                 ip_address: Optional[str] = None,
                 user_agent: Optional[str] = None,
                 description: Optional[str] = None # Optional human-readable description
                 ) -> None:
    """
    Logs an activity to the ActivityLog.
    """
    logger.debug("Logging activity", action=action_type, entity_type=entity_type, entity_id=entity_id, 
                 actor_user_id=actor_user_id, tree_id=tree_id)
    try:
        log_entry = ActivityLog(
            user_id=actor_user_id, # This is the user performing the action
            action_type=action_type,
            entity_type=entity_type,
            entity_id=entity_id,
            tree_id=tree_id,
            previous_state=previous_state,
            new_state=new_state,
            ip_address=ip_address,
            user_agent=user_agent
            # description field is not in ActivityLog model currently, so not setting it.
        )
        db.add(log_entry)
        db.commit()
        logger.info("Activity logged successfully", activity_id=log_entry.id, action=action_type, entity_type=entity_type)
    except SQLAlchemyError as e:
        # Log the error but don't abort the main operation typically
        # Or, if logging is critical, this might need to re-raise or handle differently
        db.rollback() # Rollback the log entry if commit fails
        logger.error("Failed to log activity to database.",
                     action=action_type, entity_type=entity_type, entity_id=entity_id,
                     error=str(e), exc_info=False) # Set exc_info=False to avoid huge logs for common logging failures
    except Exception as e:
        db.rollback()
        logger.error("Unexpected error while logging activity.",
                     action=action_type, entity_type=entity_type, entity_id=entity_id,
                     error=str(e), exc_info=True)
