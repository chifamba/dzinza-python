# backend/blueprints/health.py
import time
import structlog
from datetime import datetime
from flask import Blueprint, jsonify, make_response, abort
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text
from werkzeug.exceptions import HTTPException # Added for abort context

from extensions import limiter
# Import get_db_session from the database module
from database import get_db_session, get_session_factory # get_session_factory for remove()

logger = structlog.get_logger(__name__)
health_bp = Blueprint('health_api', __name__)

@health_bp.route('/health', methods=['GET'])
@limiter.limit("60 per minute")
def health_check_endpoint():
    service_status = "healthy"
    db_status = "unknown"; db_latency_ms = None
    dependencies = {}
    
    start_time_db_check = time.monotonic()
    health_db_session = None 
    try:
        # Use the thread-safe session getter
        health_db_session = get_db_session()
        if not health_db_session: # Should not happen if get_db_session is robust
            raise RuntimeError("Failed to get DB session for health check.")
            
        health_db_session.execute(text("SELECT 1"))
        # No explicit commit needed for a SELECT if session is in autocommit or if not modifying data
        db_status = "healthy"
    except SQLAlchemyError as e:
        db_status = "unhealthy"; service_status = "unhealthy"
        logger.error(f"DB health check failed (SQLAlchemyError): {e}", exc_info=False)
    except RuntimeError as re: # Catch RuntimeError from get_db_session if factory not init
        db_status = "error"; service_status = "unhealthy"
        logger.error(f"DB health check failed (RuntimeError getting session): {re}", exc_info=True)
    except Exception as e: # Catch other unexpected errors
        db_status = "error"; service_status = "unhealthy"
        logger.error(f"Unexpected error during DB health check: {e}", exc_info=True)
    finally:
        if health_db_session:
            # For scoped_session, it's good practice to remove it.
            # The session itself will be closed by the scoped_session manager.
            session_factory = get_session_factory()
            if session_factory:
                session_factory.remove() 
            # health_db_session.close() # Also acceptable, but remove() is more specific for scoped_session
        
        end_time_db_check = time.monotonic()
        db_latency_ms = (end_time_db_check - start_time_db_check) * 1000

    dependencies["database"] = {"status": db_status, "latency_ms": round(db_latency_ms, 2) if db_latency_ms is not None else None}
    
    response_data = {"status": service_status, "timestamp": datetime.utcnow().isoformat() + "Z", "dependencies": dependencies}
    http_status_code = 200 if service_status == "healthy" else 503
    
    log_level = logger.warning if service_status != "healthy" else logger.debug
    log_level("Health check status.", service_status=service_status, db_status=db_status, db_latency_ms=db_latency_ms)
        
    return jsonify(response_data), http_status_code

@health_bp.route('/metrics', methods=['GET'])
@limiter.limit("60 per minute")
def metrics_api_endpoint():
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return make_response(generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST})
    except ImportError:
        logger.error("prometheus_client not installed. /metrics unavailable.")
        abort(501, "Metrics (prometheus_client) not available.")
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}", exc_info=True)
        abort(500, "Error generating Prometheus metrics.")

