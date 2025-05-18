# backend/blueprints/health.py
"""
Defines the Flask blueprint for health check and metrics API endpoints.
"""

import time
import structlog
from datetime import datetime # For timestamp
from flask import Blueprint, jsonify, make_response, abort
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy import text

from extensions import limiter
from database import SessionLocal # For direct session usage

logger = structlog.get_logger(__name__)
health_bp = Blueprint('health_api', __name__)

@health_bp.route('/health', methods=['GET'])
@limiter.limit("60 per minute")
def health_check_endpoint():
    """
    Performs a health check of the application and its dependencies.

    Checks the database connection and reports the status of the service and its dependencies.
    """
    service_status = "healthy"
    db_status = "unknown"; db_latency_ms = None
    dependencies = {}
    
    start_time_db_check = time.monotonic()
    health_db_session = None # Initialize to None
    try:
        if not SessionLocal:
            raise RuntimeError("SessionLocal not initialized for health check.")
        health_db_session = SessionLocal()
        health_db_session.execute(text("SELECT 1"))
        db_status = "healthy"
    except SQLAlchemyError as e:
        db_status = "unhealthy"; service_status = "unhealthy"
        logger.error(f"DB health check failed: {e}", exc_info=False)
    except Exception as e:
        db_status = "error"; service_status = "unhealthy"
        logger.error(f"Unexpected error during DB health check: {e}", exc_info=True)
    finally:
        if health_db_session: health_db_session.close()
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
    """
    Provides application metrics in Prometheus exposition format.

    Handles the case where the prometheus_client library is not installed.
    """
    try:
        from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
        return make_response(generate_latest(), 200, {'Content-Type': CONTENT_TYPE_LATEST})
    except ImportError:
        logger.error("prometheus_client not installed. /metrics unavailable.")
        abort(501, "Metrics (prometheus_client) not available.")
    except Exception as e:
        logger.error(f"Error generating Prometheus metrics: {e}", exc_info=True)
        abort(500, "Error generating Prometheus metrics.")
