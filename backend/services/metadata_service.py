import json
import subprocess
from fractions import Fraction
from pathlib import Path

from backend import settings


def _fps(value: str | None) -> float:
    if not value or value == "0/0":
        return 0.0
    try:
        return round(float(Fraction(value)), 3)
    except (ValueError, ZeroDivisionError):
        return 0.0


def _run_ffprobe(path: Path) -> dict:
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
        raise RuntimeError(result.stderr.strip() or "FFprobe gagal membaca metadata.")
    return json.loads(result.stdout)


def read_metadata(path: Path) -> dict:
    data = _run_ffprobe(path)
    streams = data.get("streams", [])
    video = next((stream for stream in streams if stream.get("codec_type") == "video"), None)
    audio = next((stream for stream in streams if stream.get("codec_type") == "audio"), None)
    if not video:
        raise RuntimeError("File tidak memiliki stream video.")

    fmt = data.get("format", {})
    duration = float(video.get("duration") or fmt.get("duration") or 0)
    bitrate = int(float(video.get("bit_rate") or fmt.get("bit_rate") or 0))

    return {
        "width": int(video.get("width") or 0),
        "height": int(video.get("height") or 0),
        "resolution": f"{video.get('width', 0)}x{video.get('height', 0)}",
        "fps": _fps(video.get("avg_frame_rate") or video.get("r_frame_rate")),
        "duration": round(duration, 3),
        "video_codec": video.get("codec_name") or "unknown",
        "audio_codec": audio.get("codec_name") if audio else "none",
        "bitrate": bitrate,
        "file_size": path.stat().st_size,
    }
