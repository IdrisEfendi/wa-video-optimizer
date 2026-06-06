from pathlib import Path

from fastapi import BackgroundTasks, FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from backend import settings
from backend.services import ffmpeg_service, job_service, metadata_service, storage_service

app = FastAPI(title="WhatsApp Video Optimizer")

storage_service.ensure_storage_dirs()
app.mount("/assets", StaticFiles(directory=settings.PUBLIC_DIR / "assets"), name="assets")


class OptimizeRequest(BaseModel):
    job_id: str
    profile: str = "standard"


@app.get("/")
def index() -> FileResponse:
    return FileResponse(settings.PUBLIC_DIR / "index.html")


@app.post("/api/upload")
async def upload_video(video: UploadFile = File(...)) -> JSONResponse:
    try:
        extension = storage_service.validate_extension(video.filename or "")
        if video.content_type not in settings.ALLOWED_CONTENT_TYPES:
            raise ValueError("Tipe file tidak didukung.")

        job_id = storage_service.new_job_id()
        original_filename = storage_service.safe_filename(video.filename or f"video{extension}")
        stored_filename = f"{job_id}_original{extension}"
        upload_path = settings.UPLOAD_DIR / stored_filename

        total = 0
        with upload_path.open("wb") as target:
            while chunk := await video.read(1024 * 1024):
                total += len(chunk)
                if total > settings.MAX_UPLOAD_BYTES:
                    storage_service.remove_if_exists(upload_path)
                    raise ValueError("Ukuran file maksimal 500 MB.")
                target.write(chunk)

        metadata = metadata_service.read_metadata(upload_path)
        thumbnail_filename = f"{job_id}.jpg"
        thumbnail_path = settings.THUMBNAIL_DIR / thumbnail_filename
        try:
            ffmpeg_service.create_thumbnail(upload_path, thumbnail_path)
        except RuntimeError:
            thumbnail_filename = None

        job = job_service.create_job(
            job_id=job_id,
            original_filename=original_filename,
            stored_filename=stored_filename,
            thumbnail_filename=thumbnail_filename,
            metadata=metadata,
        )
        return JSONResponse(
            {
                "success": True,
                "job_id": job_id,
                "metadata": metadata,
                "thumbnail_url": f"/api/thumbnail/{job_id}" if thumbnail_filename else None,
                "job": job,
            }
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/api/jobs/{job_id}")
def get_job(job_id: str) -> JSONResponse:
    try:
        return JSONResponse({"success": True, "job": job_service.get_job(job_id)})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.post("/api/optimize")
def optimize_video(payload: OptimizeRequest, background_tasks: BackgroundTasks) -> JSONResponse:
    try:
        job = job_service.get_job(payload.job_id)
        if job["status"] == "processing":
            raise ValueError("Video sedang diproses.")
        job_service.update_job(payload.job_id, status="queued", progress=0, profile=payload.profile)
        background_tasks.add_task(ffmpeg_service.optimize_job, payload.job_id, payload.profile)
        return JSONResponse({"success": True, "job_id": payload.job_id, "status": "queued"})
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.get("/api/optimize/{job_id}/status")
def optimize_status(job_id: str) -> JSONResponse:
    try:
        job = job_service.get_job(job_id)
        return JSONResponse(
            {
                "success": True,
                "job_id": job_id,
                "status": job["status"],
                "progress": job.get("progress", 0),
                "error_message": job.get("error_message"),
            }
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/compare/{job_id}")
def compare(job_id: str) -> JSONResponse:
    try:
        job = job_service.get_job(job_id)
        return JSONResponse(
            {
                "success": True,
                "job_id": job_id,
                "original": job.get("original"),
                "optimized": job.get("optimized"),
                "result": job.get("result"),
                "profile": job.get("profile"),
            }
        )
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/download/{job_id}")
def download(job_id: str) -> FileResponse:
    try:
        job = job_service.get_job(job_id)
        if job.get("status") != "completed" or not job.get("output_filename"):
            raise HTTPException(status_code=404, detail="Video hasil optimasi belum tersedia.")
        path = settings.OPTIMIZED_DIR / job["output_filename"]
        return FileResponse(path, media_type="video/mp4", filename=job["output_filename"])
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/thumbnail/{job_id}")
def thumbnail(job_id: str) -> FileResponse:
    try:
        job = job_service.get_job(job_id)
        filename = job.get("thumbnail_filename")
        if not filename:
            raise HTTPException(status_code=404, detail="Thumbnail tidak tersedia.")
        return FileResponse(settings.THUMBNAIL_DIR / filename, media_type="image/jpeg")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@app.get("/api/media/{job_id}/{kind}")
def media(job_id: str, kind: str) -> FileResponse:
    try:
        job = job_service.get_job(job_id)
        if kind == "original":
            return FileResponse(settings.UPLOAD_DIR / job["stored_filename"])
        if kind == "optimized" and job.get("output_filename"):
            return FileResponse(settings.OPTIMIZED_DIR / job["output_filename"], media_type="video/mp4")
        raise HTTPException(status_code=404, detail="Media tidak tersedia.")
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
