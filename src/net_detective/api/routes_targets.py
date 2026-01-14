from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field

from net_detective.core.db import get_connection
from net_detective.core.scheduler import remove_target_job, schedule_target

router = APIRouter()


class TargetIn(BaseModel):
    name: str = Field(..., min_length=1)
    url: str = Field(..., min_length=1)
    interval_sec: int = Field(..., ge=1)
    timeout_sec: int = Field(..., ge=1)
    enabled: bool = True


class TargetOut(TargetIn):
    id: int


@router.post("/api/targets", response_model=TargetOut)
def create_target(payload: TargetIn, request: Request):
    with get_connection() as conn:
        cursor = conn.execute(
            """
            INSERT INTO targets (name, url, interval_sec, timeout_sec, enabled)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                payload.name,
                payload.url,
                payload.interval_sec,
                payload.timeout_sec,
                1 if payload.enabled else 0,
            ),
        )
        target_id = cursor.lastrowid
        row = conn.execute(
            "SELECT id, name, url, interval_sec, timeout_sec, enabled FROM targets WHERE id = ?",
            (target_id,),
        ).fetchone()

    target = dict(row)
    target["enabled"] = bool(target["enabled"])
    schedule_target(request.app.state.scheduler, target)
    return target


@router.get("/api/targets", response_model=list[TargetOut])
def list_targets():
    with get_connection() as conn:
        rows = conn.execute(
            "SELECT id, name, url, interval_sec, timeout_sec, enabled FROM targets ORDER BY id"
        ).fetchall()
    targets = []
    for row in rows:
        target = dict(row)
        target["enabled"] = bool(target["enabled"])
        targets.append(target)
    return targets


@router.put("/api/targets/{target_id}", response_model=TargetOut)
def update_target(target_id: int, payload: TargetIn, request: Request):
    with get_connection() as conn:
        conn.execute(
            """
            UPDATE targets
            SET name = ?, url = ?, interval_sec = ?, timeout_sec = ?, enabled = ?
            WHERE id = ?
            """,
            (
                payload.name,
                payload.url,
                payload.interval_sec,
                payload.timeout_sec,
                1 if payload.enabled else 0,
                target_id,
            ),
        )
        row = conn.execute(
            "SELECT id, name, url, interval_sec, timeout_sec, enabled FROM targets WHERE id = ?",
            (target_id,),
        ).fetchone()

    if not row:
        raise HTTPException(status_code=404, detail="Target not found")

    target = dict(row)
    target["enabled"] = bool(target["enabled"])
    schedule_target(request.app.state.scheduler, target)
    return target


@router.delete("/api/targets/{target_id}")
def delete_target(target_id: int, request: Request):
    with get_connection() as conn:
        row = conn.execute(
            "SELECT id FROM targets WHERE id = ?",
            (target_id,),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="Target not found")
        conn.execute("DELETE FROM targets WHERE id = ?", (target_id,))
        conn.execute("DELETE FROM probe_results WHERE target_id = ?", (target_id,))
        conn.execute("DELETE FROM alerts WHERE target_id = ?", (target_id,))

    remove_target_job(request.app.state.scheduler, target_id)
    return {"status": "deleted"}
