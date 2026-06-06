import unittest
import warnings

warnings.simplefilter("ignore", ResourceWarning)

from fastapi.testclient import TestClient

from backend.main import app
from backend.services import job_service
from backend import settings


class ConfigAndLimitsTest(unittest.TestCase):
    def test_config_endpoint_returns_runtime_settings(self):
        response = TestClient(app).get("/api/config")
        self.assertEqual(response.status_code, 200)
        config = response.json()["config"]
        self.assertEqual(config["max_upload_mb"], settings.MAX_UPLOAD_MB)
        self.assertEqual(config["max_concurrent_jobs"], settings.MAX_CONCURRENT_JOBS)
        self.assertIn(".mp4", config["allowed_extensions"])

    def test_optimize_rejects_when_concurrency_limit_reached(self):
        active_job_id = "job_active_limit_test"
        waiting_job_id = "job_waiting_limit_test"
        base_job = {
            "status": "uploaded",
            "stored_filename": "missing.mp4",
            "output_filename": None,
            "thumbnail_filename": None,
            "original": {"width": 320, "height": 180, "fps": 30, "duration": 1, "file_size": 1000},
            "expires_at": "2999-01-01T00:00:00+07:00",
        }
        job_service.save_job({"job_id": active_job_id, **base_job, "status": "queued"})
        job_service.save_job({"job_id": waiting_job_id, **base_job})

        try:
            response = TestClient(app).post("/api/optimize", json={"job_id": waiting_job_id, "profile": "standard"})
            self.assertEqual(response.status_code, 400)
            self.assertIn("Limit proses aktif", response.json()["detail"])
        finally:
            (settings.JOB_DIR / f"{active_job_id}.json").unlink(missing_ok=True)
            (settings.JOB_DIR / f"{waiting_job_id}.json").unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
