import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from backend import settings
from backend.services import storage_service


JAKARTA = timezone(timedelta(hours=7))
ACTIVE_STATUSES = {"processing", "queued", "encoding", "finalizing", "cancel_requested"}


def now_iso() -> str:
    return datetime.now(JAKARTA).isoformat(timespec="seconds")


def expires_iso() -> str:
    return (datetime.now(JAKARTA) + timedelta(hours=settings.JOB_EXPIRY_HOURS)).isoformat(timespec="seconds")


def parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def job_path(job_id: str) -> Path:
    if not job_id.startswith("job_") or not all(ch.isalnum() or ch == "_" for ch in job_id):
        raise ValueError("Job ID tidak valid.")
    return settings.JOB_DIR / f"{job_id}.json"


def save_job(job: dict[str, Any]) -> dict[str, Any]:
    path = job_path(job["job_id"])
    tmp_path = path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(job, indent=2), encoding="utf-8")
    tmp_path.replace(path)
    return job


def get_job(job_id: str) -> dict[str, Any]:
    path = job_path(job_id)
    if not path.exists():
        raise FileNotFoundError("Job tidak ditemukan.")
    return json.loads(path.read_text(encoding="utf-8"))


def list_jobs() -> list[dict[str, Any]]:
    jobs = []
    for path in settings.JOB_DIR.glob("job_*.json"):
        try:
            jobs.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            continue
    return jobs


def active_job_count() -> int:
    return sum(1 for job in list_jobs() if job.get("status") in ACTIVE_STATUSES)


def update_job(job_id: str, **updates: Any) -> dict[str, Any]:
    job = get_job(job_id)
    job.update(updates)
    return save_job(job)


def create_job(
    *,
    job_id: str,
    original_filename: str,
    stored_filename: str,
    thumbnail_filename: str | None,
    metadata: dict[str, Any],
) -> dict[str, Any]:
    job = {
        "job_id": job_id,
        "status": "uploaded",
        "profile": None,
        "original_filename": original_filename,
        "stored_filename": stored_filename,
        "output_filename": None,
        "thumbnail_filename": thumbnail_filename,
        "progress": 0,
        "original": metadata,
        "optimized": None,
        "result": None,
        "ffmpeg_args": None,
        "error_message": None,
        "created_at": now_iso(),
        "started_at": None,
        "finished_at": None,
        "expires_at": expires_iso(),
    }
    return save_job(job)


def cleanup_expired_jobs() -> dict[str, Any]:
    now = datetime.now(JAKARTA)
    removed_jobs: list[str] = []
    skipped_processing: list[str] = []

    for job in list_jobs():
        job_id = job.get("job_id")
        expires_at = parse_iso(job.get("expires_at"))
        if not job_id or not expires_at or expires_at > now:
            continue
        if job.get("status") in ACTIVE_STATUSES:
            skipped_processing.append(job_id)
            continue
        storage_service.delete_job_files(job)
        removed_jobs.append(job_id)

    return {
        "removed_count": len(removed_jobs),
        "removed_jobs": removed_jobs,
        "skipped_processing": skipped_processing,
        "storage_usage_bytes": storage_service.storage_usage_bytes(),
    }
