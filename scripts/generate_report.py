from __future__ import annotations

import os
import sqlite3
from pathlib import Path

DB_PATH = os.getenv("DB_PATH", "net_detective.db")
REPORT_PATH = Path("reports/performance_report.md")


def percentile(values: list[float], pct: float) -> float | None:
    if not values:
        return None
    values_sorted = sorted(values)
    index = int(round((pct / 100) * (len(values_sorted) - 1)))
    return values_sorted[index]


def main() -> None:
    if not Path(DB_PATH).exists():
        print(f"Database not found: {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    targets = conn.execute("SELECT id, name, url FROM targets").fetchall()
    rows = conn.execute(
        """
        SELECT target_id, status_code, response_time_ms, error
        FROM probe_results
        """
    ).fetchall()
    alerts = conn.execute("SELECT target_id FROM alerts").fetchall()

    results_by_target: dict[int, list[sqlite3.Row]] = {}
    for row in rows:
        results_by_target.setdefault(row["target_id"], []).append(row)

    alerts_by_target: dict[int, int] = {}
    for row in alerts:
        alerts_by_target[row["target_id"]] = alerts_by_target.get(row["target_id"], 0) + 1

    lines = ["# Performance Report", "", "| Target | Availability | Avg (ms) | P95 (ms) | Failures | Alerts |", "| --- | --- | --- | --- | --- | --- |"]

    def is_success(row: sqlite3.Row) -> bool:
        if row["error"]:
            return False
        if row["status_code"] is None:
            return False
        return 200 <= row["status_code"] <= 399

    for target in targets:
        target_rows = results_by_target.get(target["id"], [])
        total = len(target_rows)
        success = sum(1 for row in target_rows if is_success(row))
        failures = total - success
        response_times = [row["response_time_ms"] for row in target_rows if row["response_time_ms"] is not None]
        avg_rt = sum(response_times) / len(response_times) if response_times else None
        p95_rt = percentile(response_times, 95) if response_times else None
        availability = (success / total) if total else None
        alerts_count = alerts_by_target.get(target["id"], 0)
        lines.append(
            "| {name} | {availability} | {avg} | {p95} | {failures} | {alerts} |".format(
                name=target["name"],
                availability=f"{availability:.2%}" if availability is not None else "N/A",
                avg=f"{avg_rt:.1f}" if avg_rt is not None else "N/A",
                p95=f"{p95_rt:.1f}" if p95_rt is not None else "N/A",
                failures=failures,
                alerts=alerts_count,
            )
        )

    lines.extend(["", "Conclusion: Basic SLA metrics captured for configured targets."])

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text("\n".join(lines), encoding="utf-8")
    print(f"Report written to {REPORT_PATH}")


if __name__ == "__main__":
    main()
