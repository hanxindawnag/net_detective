import socket
import time
from datetime import datetime, timezone
from urllib.parse import urlparse

import requests

from net_detective.core.config import settings
from net_detective.core.db import get_connection


SUCCESS_MIN = 200
SUCCESS_MAX = 399


def is_success(status_code: int | None, error: str | None) -> bool:
    if error:
        return False
    if status_code is None:
        return False
    return SUCCESS_MIN <= status_code <= SUCCESS_MAX


def _measure_dns_time(hostname: str) -> tuple[float | None, str | None]:
    if not hostname:
        return None, "missing hostname"
    start = time.perf_counter()
    try:
        socket.getaddrinfo(hostname, None)
    except socket.gaierror as exc:
        return None, str(exc)
    finally:
        end = time.perf_counter()
    return (end - start) * 1000, None


def probe_target(target_id: int) -> None:
    with get_connection() as conn:
        target = conn.execute(
            "SELECT id, name, url, interval_sec, timeout_sec, enabled FROM targets WHERE id = ?",
            (target_id,),
        ).fetchone()

    if not target or not target["enabled"]:
        return

    url = target["url"]
    hostname = urlparse(url).hostname
    dns_time_ms, dns_error = _measure_dns_time(hostname or "")

    status_code = None
    response_time_ms = None
    error = ""

    if dns_error:
        error = f"DNS error: {dns_error}"
    else:
        start = time.perf_counter()
        try:
            response = requests.get(url, timeout=target["timeout_sec"])
            status_code = response.status_code
            response_time_ms = (time.perf_counter() - start) * 1000
            if not is_success(status_code, None):
                error = f"HTTP {status_code}"
        except requests.RequestException as exc:
            response_time_ms = (time.perf_counter() - start) * 1000
            error = str(exc)

    ts = datetime.now(timezone.utc).isoformat()

    with get_connection() as conn:
        conn.execute(
            """
            INSERT INTO probe_results
            (target_id, status_code, response_time_ms, dns_time_ms, error, ts)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                target_id,
                status_code,
                response_time_ms,
                dns_time_ms,
                error,
                ts,
            ),
        )

    _evaluate_alerts(target_id, status_code, response_time_ms, error, ts)


def _evaluate_alerts(
    target_id: int,
    status_code: int | None,
    response_time_ms: float | None,
    error: str,
    ts: str,
) -> None:
    alerts = []
    if response_time_ms is not None and response_time_ms > settings.threshold_ms:
        alerts.append(
            f"response_time_ms {response_time_ms:.1f} exceeded {settings.threshold_ms}"
        )

    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT status_code, error
            FROM probe_results
            WHERE target_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (target_id, settings.fail_n + 1),
        ).fetchall()

    def failure(row) -> bool:
        return not is_success(row["status_code"], row["error"])

    if len(rows) >= settings.fail_n and all(failure(row) for row in rows[: settings.fail_n]):
        previous_failure = len(rows) > settings.fail_n and failure(rows[settings.fail_n])
        if not previous_failure:
            alerts.append(f"consecutive failures reached {settings.fail_n}")

    if not alerts:
        return

    with get_connection() as conn:
        for message in alerts:
            conn.execute(
                "INSERT INTO alerts (target_id, message, ts) VALUES (?, ?, ?)",
                (target_id, message, ts),
            )
            print(f"[ALERT] target={target_id} {message} at {ts}")
