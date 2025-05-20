# backend/extensions.py
import logging
import structlog
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session as ServerSession # Renamed to avoid conflict

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
# from urllib.parse import urljoin # Not used currently

import config as app_config_module

logger = structlog.get_logger(__name__)

# Initialize extensions, but defer app binding (init_app)
cors = CORS(supports_credentials=True)
# Limiter needs storage_uri at instantiation if not using default in-memory
# It's better to init_app with config later if storage_uri depends on app.config
limiter = Limiter(key_func=get_remote_address, default_limits_exempt_when=lambda: False)
server_session_ext = ServerSession() # Renamed local variable

# OpenTelemetry
tracer_provider = None
meter_provider = None
flask_instrumentor = FlaskInstrumentor()
logging_instrumentor = LoggingInstrumentor()

# Metrics (can be accessed globally after initialization)
user_registration_counter = None
db_operation_duration_histogram = None
auth_failure_counter = None
role_change_counter = None

# Global Fernet instance, to be initialized by app factory
fernet_suite = None

def get_fernet():
    """Returns the global Fernet instance."""
    # This function is crucial for EncryptedString in models.py
    if fernet_suite is None:
        # This log indicates a potential issue if encryption is expected.
        logger.warning("get_fernet: Fernet suite accessed but is None (not initialized or key missing).")
    return fernet_suite


def init_opentelemetry(app):
    global tracer_provider, meter_provider
    global user_registration_counter, db_operation_duration_histogram, auth_failure_counter, role_change_counter

    current_config = app_config_module.config # Use the imported config object
    otel_service_name = current_config.OTEL_SERVICE_NAME
    otel_exporter_otlp_endpoint = current_config.OTEL_EXPORTER_OTLP_ENDPOINT

    if not otel_exporter_otlp_endpoint:
        logger.warning("OpenTelemetry endpoint (OTEL_EXPORTER_OTLP_ENDPOINT) not configured. OTel will not export.")
        return # Do not proceed if endpoint is not set

    resource = Resource(attributes={"service.name": otel_service_name})

    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    otlp_trace_exporter = OTLPSpanExporter(endpoint=otel_exporter_otlp_endpoint) # Assuming gRPC
    span_processor = BatchSpanProcessor(otlp_trace_exporter)
    tracer_provider.add_span_processor(span_processor)
    logger.info("OpenTelemetry Tracer configured.", endpoint=otel_exporter_otlp_endpoint)

    metric_readers = [PeriodicExportingMetricReader(OTLPMetricExporter(endpoint=otel_exporter_otlp_endpoint))]
    meter_provider = MeterProvider(resource=resource, metric_readers=metric_readers)
    metrics.set_meter_provider(meter_provider)
    logger.info("OpenTelemetry Meter configured.", endpoint=otel_exporter_otlp_endpoint)
    
    flask_instrumentor.instrument_app(app)
    # Ensure log_level matches your desired level for OTel instrumentation
    logging_instrumentor.instrument(set_logging_format=True, log_level=logging.INFO) 

    meter = metrics.get_meter(__name__) # Use app's configured meter provider
    user_registration_counter = meter.create_counter(
        "app.user.registration", description="User registration attempts", unit="1")
    db_operation_duration_histogram = meter.create_histogram(
        "db.operation.duration", description="DB operation duration", unit="ms")
    auth_failure_counter = meter.create_counter(
        "app.auth.failures", description="Authentication failures", unit="1")
    role_change_counter = meter.create_counter(
        "app.auth.role_changes", description="User role changes", unit="1")
    logger.info("Custom OpenTelemetry metrics initialized.")


def init_extensions(app):
    """Initialize Flask extensions with the app."""
    current_config = app_config_module.config # Use the imported config object
    
    cors.init_app(app, resources={r"/api/*": {"origins": current_config.CORS_ORIGINS}})
    
    # Configure Limiter with storage_uri from app config
    app.config['RATELIMIT_STORAGE_URL'] = current_config.RATELIMIT_STORAGE_URL
    app.config['RATELIMIT_DEFAULT'] = current_config.RATELIMIT_DEFAULT
    limiter.init_app(app)
    
    server_session_ext.init_app(app) # Use the renamed variable
    
    init_opentelemetry(app) # OTel init now checks for endpoint internally

    logger.info("Flask extensions initialized.")

