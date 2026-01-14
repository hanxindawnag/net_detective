from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Query

from net_detective.core.config import settings
from net_detective.core.db import get_connection
from net_detective.core.prober import is_success

router = APIRouter()


def _since(minutes: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(minutes=minutes)).isoformat()


def _since_hours(hours: int) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


@router.get("/api/dashboard/overview")
def dashboard_overview():
    window_minutes = settings.dashboard_window_minutes
    since_ts = _since(window_minutes)
    with get_connection() as conn:
        targets = conn.execute(
            "SELECT id, name, url, interval_sec, timeout_sec, enabled FROM targets ORDER BY id"
        ).fetchall()
        latest_rows = conn.execute(
            """
            SELECT pr.target_id, pr.status_code, pr.response_time_ms, pr.error, pr.ts
            FROM probe_results pr
            INNER JOIN (
                SELECT target_id, MAX(id) AS max_id
                FROM probe_results
                GROUP BY target_id
            ) grouped
            ON pr.target_id = grouped.target_id AND pr.id = grouped.max_id
            """
        ).fetchall()
        latest_map = {row["target_id"]: row for row in latest_rows}

        rows = conn.execute(
            """
            SELECT target_id, status_code, response_time_ms, error
            FROM probe_results
            WHERE ts >= ?
            """,
            (since_ts,),
        ).fetchall()

    results_by_target: dict[int, list] = {}
    for row in rows:
        results_by_target.setdefault(row["target_id"], []).append(row)

    overview_targets = []
    for target in targets:
        latest = latest_map.get(target["id"])
        recent_results = results_by_target.get(target["id"], [])
        total = len(recent_results)
        success = sum(1 for row in recent_results if is_success(row["status_code"], row["error"]))
        response_times = [
            row["response_time_ms"]
            for row in recent_results
            if row["response_time_ms"] is not None
        ]
        avg_response = (
            sum(response_times) / len(response_times)
            if response_times
            else None
        )
        overview_targets.append(
            {
                "id": target["id"],
                "name": target["name"],
                "url": target["url"],
                "enabled": bool(target["enabled"]),
                "latest_status_code": latest["status_code"] if latest else None,
                "latest_response_time_ms": latest["response_time_ms"] if latest else None,
                "latest_ts": latest["ts"] if latest else None,
                "availability": (success / total) if total else None,
                "avg_response_time_ms": avg_response,
            }
        )

    return {"window_minutes": window_minutes, "targets": overview_targets}


@router.get("/api/dashboard/timeseries")
def dashboard_timeseries(target_id: int, minutes: int = Query(60, ge=1)):
    since_ts = _since(minutes)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT ts, response_time_ms
            FROM probe_results
            WHERE target_id = ? AND ts >= ?
            ORDER BY ts ASC
            """,
            (target_id, since_ts),
        ).fetchall()

    series = [
        {"ts": row["ts"], "response_time_ms": row["response_time_ms"]}
        for row in rows
    ]
    return {"target_id": target_id, "minutes": minutes, "series": series}


@router.get("/api/dashboard/availability")
def dashboard_availability(target_id: int, hours: int = Query(24, ge=1)):
    since_ts = _since_hours(hours)
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT status_code, error
            FROM probe_results
            WHERE target_id = ? AND ts >= ?
            """,
            (target_id, since_ts),
        ).fetchall()

    total = len(rows)
    success = sum(1 for row in rows if is_success(row["status_code"], row["error"]))
    availability = (success / total) if total else None
    return {"target_id": target_id, "hours": hours, "availability": availability}
