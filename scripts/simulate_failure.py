import os
import time

import requests

BASE_URL = os.getenv("BASE_URL", "http://127.0.0.1:8000")


def main() -> None:
    payload = {
        "name": "forced-failure",
        "url": "http://127.0.0.1:1",
        "interval_sec": 5,
        "timeout_sec": 2,
        "enabled": True,
    }
    response = requests.post(f"{BASE_URL}/api/targets", json=payload, timeout=5)
    response.raise_for_status()
    target = response.json()
    print(f"Created target {target['id']}")

    wait_seconds = payload["interval_sec"] * 3
    print(f"Waiting {wait_seconds} seconds for alerts...")
    time.sleep(wait_seconds)

    alerts = requests.get(f"{BASE_URL}/api/alerts", params={"limit": 20}, timeout=5)
    alerts.raise_for_status()
    print(alerts.json())


if __name__ == "__main__":
    main()
