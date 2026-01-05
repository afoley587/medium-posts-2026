"""
app_bottlenecks.py

FastAPI + OpenTelemetry (traces) + Prometheus metrics (histograms)
INTENTIONALLY includes bottlenecks:
- Slow "DB" call (async sleep 400ms)
- Heavy "CPU" work (blocking loop on event loop!)
- Background job also slow (sleep 1200ms)

Run:
  uvicorn app_bottlenecks:app --reload --port 8000

Requires:
  pip install fastapi uvicorn \
    opentelemetry-api opentelemetry-sdk opentelemetry-exporter-otlp \
    opentelemetry-instrumentation-fastapi opentelemetry-instrumentation-asgi \
    opentelemetry-exporter-prometheus prometheus-client
"""

import asyncio
import os
import time

import uvicorn
from fastapi import BackgroundTasks, FastAPI
from opentelemetry import metrics, trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.prometheus import PrometheusMetricReader
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import make_asgi_app

RESOURCE = Resource.create({"service.name": "fastapi-demo-bottlenecks"})

trace_provider = TracerProvider(resource=RESOURCE)
otlp_traces_endpoint = os.getenv(
    "OTEL_EXPORTER_OTLP_TRACES_ENDPOINT",
    "http://jaeger:4318/v1/traces",
)

trace_exporter = OTLPSpanExporter(endpoint=otlp_traces_endpoint)
trace_provider.add_span_processor(BatchSpanProcessor(trace_exporter))
trace.set_tracer_provider(trace_provider)
tracer = trace.get_tracer(__name__)

metric_reader = PrometheusMetricReader()
meter_provider = MeterProvider(resource=RESOURCE, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

request_latency_ms = meter.create_histogram(
    name="http.server.request_duration",
    unit="ms",
    description="End-to-end request duration measured in handler",
)

bg_job_duration_ms = meter.create_histogram(
    name="background.job.duration",
    unit="ms",
    description="Background job duration",
)


app = FastAPI(title="FastAPI OTel Demo (Bottlenecks)")
FastAPIInstrumentor.instrument_app(app)

app.mount("/metrics", make_asgi_app())


async def slow_db_call_async() -> None:
    with tracer.start_as_current_span("db.query"):
        # Simulate a slow dependency
        await asyncio.sleep(0.4)


def cpu_heavy_blocking_work() -> int:
    """
    INTENTIONALLY BAD:
    This runs CPU-bound work on the event loop thread (blocking).
    """
    with tracer.start_as_current_span("cpu.work.blocking"):
        total = 0
        # A big loop that will block the event loop.
        for i in range(7_000_000):
            total += i
        return total


def slow_background_job(task_id: str) -> None:
    start = time.time()
    with tracer.start_as_current_span("background.job") as span:
        span.set_attribute("task.id", task_id)
        # Simulate slow background work
        time.sleep(1.2)

    duration_ms = (time.time() - start) * 1000.0
    bg_job_duration_ms.record(duration_ms, attributes={"task.type": "slow"})


@app.get("/items/{item_id}")
async def get_item(item_id: int) -> dict:
    start = time.time()

    with tracer.start_as_current_span("handler.get_item") as span:
        span.set_attribute("item.id", item_id)

        await slow_db_call_async()

        # INTENTIONALLY BAD: blocking CPU work in async handler
        _ = cpu_heavy_blocking_work()

        # A little extra async wait to create mixed async timing in trace
        with tracer.start_as_current_span("post.processing"):
            await asyncio.sleep(0.1)

    duration_ms = (time.time() - start) * 1000.0
    request_latency_ms.record(duration_ms, attributes={"route": "/items/{item_id}"})
    return {"item_id": item_id, "status": "ok", "mode": "bottlenecks"}


@app.post("/process/{task_id}")
async def process(task_id: str, background_tasks: BackgroundTasks) -> dict:
    # Kick off slow background work
    background_tasks.add_task(slow_background_job, task_id)
    return {"status": "queued", "task_id": task_id, "mode": "bottlenecks"}


if __name__ == "__main__":
    uvicorn.run(
        "slow:app",
        host="0.0.0.0",
        port=8000,
        access_log=True,
    )
