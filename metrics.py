"""Private Prometheus exporter for the single-worker application deployment."""
import os
import sqlite3
import time

from flask import g, request
from prometheus_client import CollectorRegistry, Counter, Histogram, ProcessCollector, PlatformCollector, start_http_server
from prometheus_client.core import GaugeMetricFamily


class TaskCollector:
    def __init__(self, database_path):
        self.database_path = database_path

    def collect(self):
        up = GaugeMetricFamily("daybook_database_up", "Whether the task database can be read")
        counts = GaugeMetricFamily("daybook_tasks", "Current task records", labels=["state"])
        try:
            with sqlite3.connect(f"file:{self.database_path}?mode=ro", uri=True, timeout=2) as connection:
                total, done = connection.execute(
                    "SELECT COUNT(*), COALESCE(SUM(completed), 0) FROM tasks"
                ).fetchone()
            up.add_metric([], 1)
            counts.add_metric(["active"], total - done)
            counts.add_metric(["completed"], done)
        except sqlite3.Error:
            up.add_metric([], 0)
        yield up
        yield counts


def install_metrics(app):
    registry = CollectorRegistry(auto_describe=True)
    PlatformCollector(registry=registry)
    if os.name == "posix":
        ProcessCollector(registry=registry)
    registry.register(TaskCollector(app.config["DATABASE"]))
    requests = Counter("daybook_http_requests_total", "Completed HTTP requests",
                       ["method", "route", "status"], registry=registry)
    duration = Histogram("daybook_http_request_duration_seconds", "HTTP response latency",
                         ["method", "route"], registry=registry,
                         buckets=(.005, .01, .025, .05, .1, .25, .5, 1, 2.5, 5))
    app.extensions["prometheus_registry"] = registry

    @app.before_request
    def start_request_timer():
        g.metrics_started = time.perf_counter()

    @app.after_request
    def record_request_metrics(response):
        started = getattr(g, "metrics_started", None)
        if started is not None:
            route = request.url_rule.rule if request.url_rule else "unmatched"
            requests.labels(request.method, route, str(response.status_code)).inc()
            duration.labels(request.method, route).observe(time.perf_counter() - started)
        return response

    # Export on a separate internal port; the public web service forwards only 8000.
    port = int(app.config.get("METRICS_PORT") or 0)
    if port and not app.testing:
        server, thread = start_http_server(port, addr="0.0.0.0", registry=registry)
        app.extensions["metrics_server"] = server
        app.extensions["metrics_thread"] = thread
