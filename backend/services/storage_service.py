import re
from pathlib import Path
from uuid import uuid4

from backend import settings


def ensure_storage_dirs() -> None:
    for directory in [
        settings.UPLOAD_DIR,
        settings.OPTIMIZED_DIR,
        settings.THUMBNAIL_DIR,
        settings.JOB_DIR,
        settings.LOG_DIR,
    ]:
        directory.mkdir(parents=True, exist_ok=True)


def new_job_id() -> str:
    return f"job_{uuid4().hex}"


def safe_filename(filename: str) -> str:
    stem = Path(filename).stem.strip() or "video"
    suffix = Path(filename).suffix.lower()
    safe_stem = re.sub(r"[^A-Za-z0-9._-]+", "_", stem).strip("._-") or "video"
    return f"{safe_stem}{suffix}"


def validate_extension(filename: str) -> str:
    extension = Path(filename).suffix.lower()
    if extension not in settings.ALLOWED_EXTENSIONS:
        raise ValueError("Format video tidak didukung.")
    return extension


def remove_if_exists(path: Path | None) -> None:
    if path and path.exists() and path.is_file():
        path.unlink()


def delete_job_files(job: dict) -> None:
    stored_filename = job.get("stored_filename")
    output_filename = job.get("output_filename")
    thumbnail_filename = job.get("thumbnail_filename")
    job_id = job.get("job_id")

    if stored_filename:
        remove_if_exists(settings.UPLOAD_DIR / stored_filename)
    if output_filename:
        remove_if_exists(settings.OPTIMIZED_DIR / output_filename)
    if thumbnail_filename:
        remove_if_exists(settings.THUMBNAIL_DIR / thumbnail_filename)
    if job_id:
        remove_if_exists(settings.LOG_DIR / f"{job_id}.ffmpeg.log")
    remove_if_exists(settings.JOB_DIR / f"{job['job_id']}.json")


def storage_usage_bytes() -> int:
    total = 0
    for directory in [settings.UPLOAD_DIR, settings.OPTIMIZED_DIR, settings.THUMBNAIL_DIR, settings.JOB_DIR, settings.LOG_DIR]:
        if directory.exists():
            total += sum(path.stat().st_size for path in directory.rglob("*") if path.is_file())
    return total
