from fastapi import APIRouter, Query

from net_detective.core.db import get_connection

router = APIRouter()


@router.get("/api/alerts")
def list_alerts(limit: int = Query(50, ge=1, le=500)):
    with get_connection() as conn:
        rows = conn.execute(
            """
            SELECT id, target_id, message, ts
            FROM alerts
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()
    alerts = [dict(row) for row in rows]
    return {"alerts": alerts}
