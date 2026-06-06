import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
OPTIMIZED_DIR = STORAGE_DIR / "optimized"
THUMBNAIL_DIR = STORAGE_DIR / "thumbnails"
JOB_DIR = STORAGE_DIR / "jobs"
LOG_DIR = STORAGE_DIR / "logs"


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


MAX_UPLOAD_MB = _int_env("WA_MAX_UPLOAD_MB", 500)
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
    "application/octet-stream",
}

FFMPEG_BIN = os.environ.get("WA_FFMPEG_BIN", "ffmpeg")
FFPROBE_BIN = os.environ.get("WA_FFPROBE_BIN", "ffprobe")
JOB_EXPIRY_HOURS = _int_env("WA_JOB_EXPIRY_HOURS", 24)
MAX_CONCURRENT_JOBS = max(_int_env("WA_MAX_CONCURRENT_JOBS", 1), 1)
