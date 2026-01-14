from fastapi import FastAPI

from net_detective.api import alerts_router, dashboard_router, health_router, targets_router
from net_detective.core.db import get_connection, init_db
from net_detective.core.scheduler import create_scheduler, schedule_target


def create_app() -> FastAPI:
    app = FastAPI(title="Net Detective")

    app.include_router(health_router)
    app.include_router(targets_router)
    app.include_router(dashboard_router)
    app.include_router(alerts_router)

    @app.on_event("startup")
    def startup_event() -> None:
        init_db()
        scheduler = create_scheduler()
        scheduler.start()
        app.state.scheduler = scheduler

        with get_connection() as conn:
            targets = conn.execute(
                "SELECT id, name, url, interval_sec, timeout_sec, enabled FROM targets"
            ).fetchall()

        for target in targets:
            schedule_target(scheduler, dict(target))

    @app.on_event("shutdown")
    def shutdown_event() -> None:
        scheduler = getattr(app.state, "scheduler", None)
        if scheduler:
            scheduler.shutdown(wait=False)

    return app


app = create_app()
