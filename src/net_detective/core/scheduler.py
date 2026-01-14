from apscheduler.schedulers.background import BackgroundScheduler

from net_detective.core.prober import probe_target


def create_scheduler() -> BackgroundScheduler:
    scheduler = BackgroundScheduler(timezone="UTC")
    return scheduler


def job_id_for(target_id: int) -> str:
    return f"target_{target_id}"


def schedule_target(scheduler: BackgroundScheduler, target: dict) -> None:
    if target.get("enabled"):
        scheduler.add_job(
            probe_target,
            "interval",
            seconds=target["interval_sec"],
            id=job_id_for(target["id"]),
            replace_existing=True,
            args=[target["id"]],
        )
    else:
        remove_target_job(scheduler, target["id"])


def remove_target_job(scheduler: BackgroundScheduler, target_id: int) -> None:
    job_id = job_id_for(target_id)
    if scheduler.get_job(job_id):
        scheduler.remove_job(job_id)
