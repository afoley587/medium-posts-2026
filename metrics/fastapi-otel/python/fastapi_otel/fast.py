"""
app_optimized.py

Same app, but bottlenecks removed:
- DB call "optimized" (async sleep 80ms)
- CPU work moved off event loop via asyncio.to_thread + reduced work
- Background job optimized (sleep 200ms) and still traced + metered

Run:
  uvicorn app_optimized:app --reload --port 8001
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

RESOURCE = Resource.create({"service.name": "fastapi-demo-optimized"})

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

app = FastAPI(title="FastAPI OTel Demo (Optimized)")
FastAPIInstrumentor.instrument_app(app)

app.mount("/metrics", make_asgi_app())


async def faster_db_call_async() -> None:
    with tracer.start_as_current_span("db.query"):
        # Simulate faster dependency (e.g., caching, better indexing)
        await asyncio.sleep(0.08)


def cpu_work_smaller() -> int:
    """
    Still CPU-bound, but reduced. More importantly, we won't run it on the event loop.
    """
    with tracer.start_as_current_span("cpu.work"):
        total = 0
        for i in range(7_000_000):
            total += i
        return total


async def cpu_work_off_event_loop() -> int:
    # Move CPU-bound work off the event loop thread
    with tracer.start_as_current_span("cpu.work.offloaded"):
        return await asyncio.to_thread(cpu_work_smaller)


def faster_background_job(task_id: str) -> None:
    start = time.time()
    with tracer.start_as_current_span("background.job") as span:
        span.set_attribute("task.id", task_id)
        # Simulate optimized background work
        time.sleep(0.2)

    duration_ms = (time.time() - start) * 1000.0
    bg_job_duration_ms.record(duration_ms, attributes={"task.type": "fast"})


@app.get("/items/{item_id}")
async def get_item(item_id: int) -> dict:
    start = time.time()

    with tracer.start_as_current_span("handler.get_item") as span:
        span.set_attribute("item.id", item_id)

        await faster_db_call_async()

        # Optimized: offload CPU work
        _ = await cpu_work_off_event_loop()

        with tracer.start_as_current_span("post.processing"):
            await asyncio.sleep(0.02)

    duration_ms = (time.time() - start) * 1000.0
    request_latency_ms.record(duration_ms, attributes={"route": "/items/{item_id}"})
    return {"item_id": item_id, "status": "ok", "mode": "optimized"}


@app.post("/process/{task_id}")
async def process(task_id: str, background_tasks: BackgroundTasks) -> dict:
    background_tasks.add_task(faster_background_job, task_id)
    return {"status": "queued", "task_id": task_id, "mode": "optimized"}


if __name__ == "__main__":
    uvicorn.run(
        "fast:app",
        host="0.0.0.0",
        port=8000,
        access_log=True,
    )
