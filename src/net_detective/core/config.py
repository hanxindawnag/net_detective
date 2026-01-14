import os
from dataclasses import dataclass

from dotenv import load_dotenv

load_dotenv()


@dataclass(frozen=True)
class Settings:
    db_path: str
    threshold_ms: int
    fail_n: int
    dashboard_window_minutes: int


settings = Settings(
    db_path=os.getenv("DB_PATH", "net_detective.db"),
    threshold_ms=int(os.getenv("THRESHOLD_MS", "1500")),
    fail_n=int(os.getenv("FAIL_N", "3")),
    dashboard_window_minutes=int(os.getenv("DASHBOARD_WINDOW_MINUTES", "60")),
)
