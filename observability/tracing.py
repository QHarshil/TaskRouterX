from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
import os
from dotenv import load_dotenv
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Check if tracing is enabled
ENABLE_TRACING = os.getenv("ENABLE_TRACING", "true").lower() == "true"


def setup_tracing(app=None, engine=None):
    """
    Set up OpenTelemetry tracing.
    
    Args:
        app (FastAPI, optional): FastAPI application to instrument
        engine (Engine, optional): SQLAlchemy engine to instrument
    """
    if not ENABLE_TRACING:
        logger.info("Tracing is disabled")
        return

    try:
        # Set up tracer provider
        tracer_provider = TracerProvider()
        trace.set_tracer_provider(tracer_provider)
        
        # Set up exporter
        otlp_exporter = OTLPSpanExporter(endpoint=os.getenv("OTLP_ENDPOINT", "localhost:4317"))
        span_processor = BatchSpanProcessor(otlp_exporter)
        tracer_provider.add_span_processor(span_processor)
        
        # Instrument FastAPI if provided
        if app:
            FastAPIInstrumentor.instrument_app(app)
            logger.info("FastAPI instrumented for tracing")
        
        # Instrument Redis
        RedisInstrumentor().instrument()
        logger.info("Redis instrumented for tracing")
        
        # Instrument SQLAlchemy if engine provided
        if engine:
            SQLAlchemyInstrumentor().instrument(engine=engine)
            logger.info("SQLAlchemy instrumented for tracing")
            
        logger.info("OpenTelemetry tracing set up successfully")
    except Exception as e:
        logger.error(f"Failed to set up tracing: {e}")


def get_tracer():
    """
    Get a tracer for manual instrumentation.
    
    Returns:
        Tracer: OpenTelemetry tracer
    """
    return trace.get_tracer("taskrouterx.tracer")
