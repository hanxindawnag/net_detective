from net_detective.api.routes_alerts import router as alerts_router
from net_detective.api.routes_dashboard import router as dashboard_router
from net_detective.api.routes_health import router as health_router
from net_detective.api.routes_targets import router as targets_router

__all__ = [
    "alerts_router",
    "dashboard_router",
    "health_router",
    "targets_router",
]
