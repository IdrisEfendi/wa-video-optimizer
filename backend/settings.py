from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
PUBLIC_DIR = BASE_DIR / "public"
STORAGE_DIR = BASE_DIR / "storage"
UPLOAD_DIR = STORAGE_DIR / "uploads"
OPTIMIZED_DIR = STORAGE_DIR / "optimized"
THUMBNAIL_DIR = STORAGE_DIR / "thumbnails"
JOB_DIR = STORAGE_DIR / "jobs"
LOG_DIR = STORAGE_DIR / "logs"

MAX_UPLOAD_BYTES = 500 * 1024 * 1024
ALLOWED_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
ALLOWED_CONTENT_TYPES = {
    "video/mp4",
    "video/quicktime",
    "video/x-msvideo",
    "video/x-matroska",
    "video/webm",
    "application/octet-stream",
}

FFMPEG_BIN = "ffmpeg"
FFPROBE_BIN = "ffprobe"
JOB_EXPIRY_HOURS = 24
