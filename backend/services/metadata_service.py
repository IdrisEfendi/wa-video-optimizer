import json
import subprocess
from fractions import Fraction
from pathlib import Path

from backend import settings


class InvalidVideoError(ValueError):
    pass


def _fps(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    try:
        return round(float(Fraction(value)), 3)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _run_ffprobe(path: Path) -> dict:
    if not path.exists() or path.stat().st_size <= 0:
        raise InvalidVideoError("File video kosong atau tidak terbaca.")

    result = subprocess.run(
        [
            settings.FFPROBE_BIN,
            "-v",
            "error",
            "-print_format",
            "json",
            "-show_format",
            "-show_streams",
            str(path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise InvalidVideoError("File tidak bisa dibaca sebagai video valid.")
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as exc:
        raise InvalidVideoError("Metadata video tidak valid.") from exc


def read_metadata(path: Path) -> dict:
    data = _run_ffprobe(path)
    streams = data.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video:
        raise InvalidVideoError("File tidak memiliki stream video.")

    fmt = data.get("format", {})
    duration = float(video.get("duration") or fmt.get("duration") or 0)
    bitrate = int(float(video.get("bit_rate") or fmt.get("bit_rate") or 0))
    width = int(video.get("width") or 0)
    height = int(video.get("height") or 0)
    fps = _fps(video.get("avg_frame_rate") or video.get("r_frame_rate"))

    if width <= 0 or height <= 0:
        raise InvalidVideoError("Resolusi video tidak valid.")
    if duration <= 0:
        raise InvalidVideoError("Durasi video tidak valid atau tidak bisa dibaca.")
    if fps <= 0:
        raise InvalidVideoError("FPS video tidak valid atau tidak bisa dibaca.")

    return {
        "width": width,
        "height": height,
        "resolution": f"{width}x{height}",
        "fps": fps,
        "duration": round(duration, 3),
        "video_codec": video.get("codec_name") or "unknown",
        "audio_codec": audio.get("codec_name") if audio else "none",
        "bitrate": bitrate,
        "file_size": path.stat().st_size,
    }
