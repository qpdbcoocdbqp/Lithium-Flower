import asyncio
import logging
import sys
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Constants for LightningStore resource attributes
ROLLOUT_ID_ATTR = "agentlightning.rollout_id"
ATTEMPT_ID_ATTR = "agentlightning.attempt_id"

def main():
    # 1. Define Resource with required AgentLightning attributes
    # These are required for LightningStore to accept the traces and associate them with a rollout/attempt.
    resource = Resource.create({
        "service.name": "agl-otel-example",
        ROLLOUT_ID_ATTR: "example-rollout-123",
        ATTEMPT_ID_ATTR: "example-attempt-456",
    })

    # 2. Initialize TracerProvider with the resource
    provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(provider)

    # 3. Configure Exporter for LightningStore
    # LightningStore accepts OTLP traces at /v1/traces
    # Default port is 4747
    agl_store_endpoint = "http://localhost:4747/v1/traces"
    agl_exporter = OTLPSpanExporter(endpoint=agl_store_endpoint)
    agl_processor = BatchSpanProcessor(agl_exporter)
    provider.add_span_processor(agl_processor)
    logger.info(f"Added OTLP exporter for LightningStore at {agl_store_endpoint}")

    # 4. Configure Exporter for External OTel Collector / Jaeger
    # Standard OTLP HTTP endpoint is usually 4318
    jaeger_endpoint = "http://localhost:4318/v1/traces"
    jaeger_exporter = OTLPSpanExporter(endpoint=jaeger_endpoint)
    jaeger_processor = BatchSpanProcessor(jaeger_exporter)
    provider.add_span_processor(jaeger_processor)
    logger.info(f"Added OTLP exporter for Jaeger/Collector at {jaeger_endpoint}")

    # 5. Create a Tracer and generate spans
    tracer = trace.get_tracer("agl-otel-tracer")

    logger.info("Generating spans...")
    with tracer.start_as_current_span("root_span") as root:
        root.set_attribute("example.attribute", "root_value")
        
        with tracer.start_as_current_span("child_span") as child:
            child.set_attribute("example.attribute", "child_value")
            child.add_event("something_happened")
            
            # Simulate some work
            import time
            time.sleep(0.1)

    logger.info("Spans generated. Flushing...")
    
    # Force flush to ensure spans are sent before script exits
    provider.force_flush()
    logger.info("Done.")

if __name__ == "__main__":
    main()
