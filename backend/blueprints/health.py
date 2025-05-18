# backend/blueprints/health.py
import time
import structlog
from flask import Blueprint, jsonify, make_response, current_app, abort
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text # For executing raw SQL

from ..extensions import limiter # Import limiter instance
from ..database import SessionLocal # To create a new session for health check

logger = structlog.get_logger(__name__)
health_bp = Blueprint('health_api', __name__) # No URL prefix, routes are top-level

@health_bp.route('/health', methods=['GET'])
@limiter.limit("60 per minute")
def health_check_endpoint():
    service_status = "healthy"
    db_status = "unknown"
    db_latency_ms = None
    dependencies = {}
    
    start_time_db_check = time.monotonic()
    db_session_for_health = None
    try:
        if not SessionLocal:
            raise RuntimeError("SessionLocal not initialized for health check.")
        db_session_for_health = SessionLocal()
        db_session_for_health.execute(text("SELECT 1"))
        db_status = "healthy"
    except SQLAlchemyError as e:
        db_status = "unhealthy"
        service_status = "unhealthy"
        logger.error(f"Database health check failed: {e}", exc_info=False)
    except Exception as e: # Catch other errors like SessionLocal not init
        db_status = "error"
        service_status = "unhealthy"
        logger.error(f"Unexpected error during DB health check: {e}", exc_info=True)
    finally:
        if db_session_for_health:
            db_session_for_health.close()
        end_time_db_check = time.monotonic()
        db_latency_ms = (end_time_db_check - start_time_db_check) * 1000

    dependencies["database"] = {
        "status": db_status,
        "latency_ms": round(db_latency_ms, 2) if db_latency_ms is not None else None
    }
    
    response_data = {
        "status": service_status,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "dependencies": dependencies
    }
    http_status_code = 200 if service_status == "healthy" else 503
    
    log_level = logger.warning if service_status != "healthy" else logger.debug
    log_level("Health check status.", service_overall_status=service_status, db_status=db_status, db_latency_ms=db_latency_ms)
        
    return jsonify(response_data), http_status_code

@health_bp.route('/metrics', methods=['GET'])
@limiter.limit("60 per minute")
def metrics_api_endpoint(): # Renamed
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        prometheus_response_body = generate_latest()
        response = make_response(prometheus_response_body)
        response.headers['Content-Type'] = CONTENT_TYPE_LATEST
        return response
    except ImportError:
        logger.error("prometheus_client library not installed. /metrics endpoint unavailable.")
        abort(501, "Metrics endpoint (prometheus_client) not available.")
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}", exc_info=True)
        abort(500, "Error generating Prometheus metrics.")

