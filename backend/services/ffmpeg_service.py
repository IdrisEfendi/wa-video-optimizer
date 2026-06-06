import subprocess
import time
from pathlib import Path

from backend import settings
from backend.services import job_service, metadata_service, profile_service


def create_thumbnail(input_path: Path, output_path: Path) -> None:
    result = subprocess.run(
        [
            settings.FFMPEG_BIN,
            "-y",
            "-hide_banner",
            "-loglevel",
            "error",
            "-ss",
            "00:00:01",
            "-i",
            str(input_path),
            "-frames:v",
            "1",
            "-q:v",
            "2",
            str(output_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "Gagal membuat thumbnail.")


def build_ffmpeg_args(input_path: Path, output_path: Path, metadata: dict, profile_name: str) -> list[str]:
    profile = profile_service.get_profile(profile_name)
    fps = profile_service.output_fps(metadata)
    vf = profile_service.video_filter(metadata, profile)
    maxrate, bufsize = profile_service.bitrate_cap(metadata, profile)

    return [
        settings.FFMPEG_BIN,
        "-y",
        "-hide_banner",
        "-loglevel",
        "error",
        "-i",
        str(input_path),
        "-map",
        "0:v:0",
        "-map",
        "0:a?",
        "-c:v",
        "libx264",
        "-crf",
        str(profile.crf),
        "-preset",
        "medium",
        "-r",
        f"{fps:g}",
        "-vf",
        vf,
        "-maxrate",
        maxrate,
        "-bufsize",
        bufsize,
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        "-c:a",
        "aac",
        "-b:a",
        "128k",
        "-ac",
        "2",
        "-ar",
        "44100",
        "-progress",
        "pipe:1",
        "-nostats",
        str(output_path),
    ]


def optimize_job(job_id: str, profile_name: str) -> None:
    job = job_service.get_job(job_id)
    input_path = settings.UPLOAD_DIR / job["stored_filename"]
    output_filename = f"{job_id}_optimized.mp4"
    output_path = settings.OPTIMIZED_DIR / output_filename
    started = time.monotonic()

    try:
        args = build_ffmpeg_args(input_path, output_path, job["original"], profile_name)
        job.update(
            {
                "status": "processing",
                "profile": profile_name,
                "output_filename": output_filename,
                "progress": 1,
                "started_at": job_service.now_iso(),
                "ffmpeg_args": args,
                "error_message": None,
            }
        )
        job_service.save_job(job)

        duration_ms = max(float(job["original"].get("duration") or 0) * 1_000_000, 1)
        log_path = settings.LOG_DIR / f"{job_id}.ffmpeg.log"
        with log_path.open("w", encoding="utf-8") as log_file:
            process = subprocess.Popen(
                args,
                stdout=subprocess.PIPE,
                stderr=log_file,
                text=True,
                bufsize=1,
            )

            if process.stdout:
                for line in process.stdout:
                    key, _, value = line.strip().partition("=")
                    if key == "out_time_ms":
                        progress = min(int((int(value) / duration_ms) * 100), 99)
                        job = job_service.get_job(job_id)
                        job["progress"] = max(job.get("progress", 0), progress)
                        job_service.save_job(job)

            returncode = process.wait()
        if returncode != 0:
            message = log_path.read_text(encoding="utf-8").strip()
            raise RuntimeError(message or "FFmpeg gagal memproses video.")
        if not output_path.exists() or output_path.stat().st_size == 0:
            raise RuntimeError("Output video tidak terbentuk.")

        optimized = metadata_service.read_metadata(output_path)
        original_size = int(job["original"].get("file_size") or 0)
        optimized_size = int(optimized.get("file_size") or 0)
        saved = max(original_size - optimized_size, 0)
        reduction = round((saved / original_size) * 100, 2) if original_size else 0
        processing_seconds = round(time.monotonic() - started, 3)

        job = job_service.get_job(job_id)
        job.update(
            {
                "status": "completed",
                "progress": 100,
                "optimized": optimized,
                "result": {
                    "reduction_percent": reduction,
                    "saved_bytes": saved,
                    "processing_seconds": processing_seconds,
                },
                "finished_at": job_service.now_iso(),
            }
        )
        job_service.save_job(job)
    except Exception as exc:
        job = job_service.get_job(job_id)
        job.update(
            {
                "status": "failed",
                "error_message": str(exc),
                "finished_at": job_service.now_iso(),
            }
        )
        job_service.save_job(job)
