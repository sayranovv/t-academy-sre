import json
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.request import urlopen

import pytest
from prometheus_client import CollectorRegistry, start_http_server

from app import prober


@pytest.fixture
def target():
    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/slow":
                time.sleep(0.15)
            self.send_response(503 if self.path == "/unavailable" else 200)
            self.end_headers()
            body = {
                "/ready": {"status": "ready", "database": "connected"},
                "/wrong": {"status": "alive"},
            }.get(self.path, {})
            try:
                self.wfile.write(
                    b"not json" if self.path == "/invalid" else json.dumps(body).encode()
                )
            except OSError:
                pass  # A timed-out probe may already have closed the connection.

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=lambda: server.serve_forever(poll_interval=0.01))
    thread.start()
    yield f"http://127.0.0.1:{server.server_port}"
    server.shutdown()
    server.server_close()
    thread.join()


@pytest.mark.parametrize(
    ("path", "successful", "reason"),
    [
        ("/ready", True, "ready"),
        ("/unavailable", False, "http_or_connection_error"),
        ("/wrong", False, "invalid_body"),
        ("/invalid", False, "invalid_body"),
        ("/slow", False, "timeout"),
    ],
)
def test_check_ready_over_http(target, path, successful, reason):
    timeout = 0.05 if path == "/slow" else 2
    assert prober.check_ready(prober.Settings(target + path, timeout=timeout)) == (
        successful,
        reason,
    )


def test_failed_check_does_not_stop_loop_and_metrics_are_exported(monkeypatch):
    registry = CollectorRegistry()
    checks = prober.make_counter(registry)
    stop = threading.Event()
    results = iter([(False, "timeout"), (True, "ready")])

    def check(settings):
        result = next(results)
        if result[0]:
            stop.set()
        return result

    monkeypatch.setattr(prober, "check_ready", check)
    prober.run_checks(
        prober.Settings("http://localhost/health/ready", interval=0.001), checks, stop
    )
    server, thread = start_http_server(0, addr="127.0.0.1", registry=registry)
    try:
        with urlopen(f"http://127.0.0.1:{server.server_port}/metrics", timeout=2) as response:
            body = response.read().decode()
        assert 'probe_checks_total{result="success"} 1.0' in body
        assert 'probe_checks_total{result="failure"} 1.0' in body
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def test_invalid_configuration_fails_fast():
    with pytest.raises(ValueError):
        prober.Settings("http://localhost", interval=float("nan"))
    with pytest.raises(ValueError):
        prober.Settings("http://localhost", timeout=0)
    with pytest.raises(ValueError):
        prober.Settings("file:///tmp/health")
