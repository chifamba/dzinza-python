# backend/extensions.py
import structlog
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session as ServerSession

from opentelemetry import trace, metrics
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter # Assuming gRPC
# from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter as OTLPSpanExporterHTTP # If HTTP
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter # Assuming gRPC
# from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter as OTLPMetricExporterHTTP # If HTTP
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from urllib.parse import urljoin

from .config import config # Import the application config

logger = structlog.get_logger(__name__)

# Initialize extensions, but defer app binding (init_app)
cors = CORS(supports_credentials=True) # resources managed in app factory
limiter = Limiter(key_func=get_remote_address, storage_uri=config.REDIS_URL, default_limits_exempt_when=lambda: False)
server_side_session = ServerSession()

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


def init_opentelemetry(app):
    """Initializes OpenTelemetry for the Flask app."""
    global tracer_provider, meter_provider
    global user_registration_counter, db_operation_duration_histogram, auth_failure_counter, role_change_counter

    otel_service_name = config.OTEL_SERVICE_NAME
    otel_exporter_otlp_endpoint = config.OTEL_EXPORTER_OTLP_ENDPOINT

    resource = Resource(attributes={"service.name": otel_service_name})

    # Tracer Provider
    tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer_provider)
    
    otlp_trace_exporter_args = {}
    if otel_exporter_otlp_endpoint:
        # For gRPC, endpoint is like "host:port". For HTTP, it's "http://host:port/v1/traces"
        # Assuming gRPC for OTLPSpanExporter by default
        otlp_trace_exporter_args["endpoint"] = otel_exporter_otlp_endpoint 
        # If using HTTP Exporter:
        # otlp_trace_exporter_args["endpoint"] = urljoin(otel_exporter_otlp_endpoint, "v1/traces")

    otlp_trace_exporter = OTLPSpanExporter(**otlp_trace_exporter_args)
    span_processor = BatchSpanProcessor(otlp_trace_exporter)
    tracer_provider.add_span_processor(span_processor)
    logger.info("OpenTelemetry Tracer configured.", exporter_args=otlp_trace_exporter_args)

    # Meter Provider
    meter_provider = MeterProvider(resource=resource, metric_readers=[]) # Add readers later
    metrics.set_meter_provider(meter_provider)

    otlp_metric_exporter_args = {}
    if otel_exporter_otlp_endpoint:
        # Assuming gRPC for OTLPMetricExporter by default
        otlp_metric_exporter_args["endpoint"] = otel_exporter_otlp_endpoint
        # If using HTTP Exporter:
        # otlp_metric_exporter_args["endpoint"] = urljoin(otel_exporter_otlp_endpoint, "v1/metrics")

    otlp_metric_exporter = OTLPMetricExporter(**otlp_metric_exporter_args)
    metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter)
    meter_provider.add_metric_reader(metric_reader)
    logger.info("OpenTelemetry Meter configured.", exporter_args=otlp_metric_exporter_args)
    
    # Instrument Flask app and logging
    flask_instrumentor.instrument_app(app)
    logging_instrumentor.instrument(set_logging_format=True, log_level=logging.INFO) # Match app's log level

    # Initialize custom metrics
    meter = metrics.get_meter(__name__)
    user_registration_counter = meter.create_counter(
        name="app.user.registration",
        description="Counts user registration attempts and successes",
        unit="1"
    )
    db_operation_duration_histogram = meter.create_histogram(
        name="db.operation.duration",
        description="Records the duration of database operations",
        unit="ms"
    )
    auth_failure_counter = meter.create_counter(
        name="app.auth.failures",
        description="Counts authentication failures",
        unit="1"
    )
    role_change_counter = meter.create_counter(
        name="app.auth.role_changes",
        description="Counts user role changes",
        unit="1"
    )
    logger.info("Custom OpenTelemetry metrics initialized.")


def init_extensions(app):
    """Initialize Flask extensions with the app."""
    cors.init_app(app, resources={r"/api/*": {"origins": config.CORS_ORIGINS}})
    limiter.init_app(app)
    server_side_session.init_app(app)
    
    if config.OTEL_EXPORTER_OTLP_ENDPOINT: # Only init OTel if endpoint is configured
        init_opentelemetry(app)
    else:
        logger.warning("OpenTelemetry endpoint not configured (OTEL_EXPORTER_OTLP_ENDPOINT). OTel disabled.")

    logger.info("Flask extensions initialized.")

# Global Fernet instance, initialized by the app factory
fernet_suite = None

def get_fernet():
    """Returns the global Fernet instance."""
    if fernet_suite is None:
        # This should ideally not happen if app initialization is correct.
        # Consider raising an error or logging a critical message.
        logger.critical("Fernet suite accessed before initialization!")
    return fernet_suite

