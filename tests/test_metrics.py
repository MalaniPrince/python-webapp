import sys
from pathlib import Path

from prometheus_client import generate_latest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app import create_app


def test_request_metrics_and_database_counts(tmp_path):
    app = create_app({"TESTING": True, "DATA_DIR": str(tmp_path)})
    client = app.test_client()
    client.get("/")
    client.get("/healthz")
    client.get("/missing-123")
    client.get("/missing-456")
    output = generate_latest(app.extensions["prometheus_registry"]).decode()
    assert 'daybook_http_requests_total{method="GET",route="/",status="200"} 1.0' in output
    assert 'route="unmatched",status="404"} 2.0' in output
    assert 'missing-123' not in output
    assert 'daybook_http_request_duration_seconds_count{method="GET",route="/"} 1.0' in output
    assert 'daybook_database_up 1.0' in output
    assert 'daybook_tasks{state="active"} 0.0' in output
    assert client.get("/metrics").status_code == 404


def test_application_factories_have_independent_registries(tmp_path):
    app1 = create_app({"TESTING": True, "DATA_DIR": str(tmp_path/"one")})
    app2 = create_app({"TESTING": True, "DATA_DIR": str(tmp_path/"two")})
    app1.test_client().get("/healthz")
    assert 'daybook_http_requests_total{' in generate_latest(app1.extensions['prometheus_registry']).decode()
    assert 'daybook_http_requests_total{' not in generate_latest(app2.extensions['prometheus_registry']).decode()
