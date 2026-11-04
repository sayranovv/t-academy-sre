"""Независимый HTTP-пробер; не импортирует приложение и не подключается к БД."""

import json
import logging
import math
import os
import signal
import time
from dataclasses import dataclass
from http.client import HTTPException
from threading import Event
from urllib.error import URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, ProxyHandler, build_opener

from prometheus_client import CollectorRegistry, Counter, start_http_server

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Settings:
    target_url: str
    interval: float = 30
    timeout: float = 5
    port: int = 9101

    def __post_init__(self):
        url = urlsplit(self.target_url)
        if url.scheme not in {"http", "https"} or not url.hostname or url.username or url.password:
            raise ValueError("PROBE_TARGET_URL must be an HTTP(S) URL without credentials")
        if not all(math.isfinite(v) and v > 0 for v in (self.interval, self.timeout)):
            raise ValueError("Probe interval and timeout must be finite positive numbers")
        if not 1 <= self.port <= 65535:
            raise ValueError("PROBE_METRICS_PORT must be between 1 and 65535")

    @classmethod
    def from_env(cls):
        return cls(
            target_url=os.environ["PROBE_TARGET_URL"],
            interval=float(os.getenv("PROBE_INTERVAL_SECONDS", "30")),
            timeout=float(os.getenv("PROBE_TIMEOUT_SECONDS", "5")),
            port=int(os.getenv("PROBE_METRICS_PORT", "9101")),
        )


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def check_ready(settings: Settings) -> tuple[bool, str]:
    # Direct requests: do not route cluster-local checks through an environment proxy.
    opener = build_opener(ProxyHandler({}), NoRedirect())
    started = time.monotonic()
    try:
        with opener.open(settings.target_url, timeout=settings.timeout) as response:
            if response.status != 200:
                return False, "http_status"
            body = response.read(16385)
        if time.monotonic() - started > settings.timeout:
            return False, "timeout"
        if len(body) > 16384:
            return False, "invalid_body"
        payload = json.loads(body)
        if not isinstance(payload, dict) or (
            payload.get("status") != "ready" or payload.get("database") != "connected"
        ):
            return False, "invalid_body"
    except TimeoutError:
        return False, "timeout"
    except OSError, URLError, HTTPException:
        return False, "http_or_connection_error"
    except ValueError, UnicodeError:
        return False, "invalid_body"
    return True, "ready"


def make_counter(registry: CollectorRegistry) -> Counter:
    checks = Counter(
        "probe_checks_total",
        "Completed readiness checks of the equipment application",
        ["result"],
        registry=registry,
    )
    for result in ("success", "failure"):
        checks.labels(result=result)
    return checks


def run_checks(settings: Settings, checks: Counter, stop: Event):
    while not stop.is_set():
        started = time.monotonic()
        successful, reason = check_ready(settings)
        checks.labels(result="success" if successful else "failure").inc()
        logger.info("Readiness check result=%s reason=%s", successful, reason)
        # Keep start-to-start cadence; never overlap checks or retry within a check.
        stop.wait(max(0, settings.interval - (time.monotonic() - started)))


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    settings = Settings.from_env()
    registry = CollectorRegistry()
    checks = make_counter(registry)
    stop = Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())
    server, thread = start_http_server(settings.port, registry=registry)
    try:
        run_checks(settings, checks, stop)
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


if __name__ == "__main__":
    main()
