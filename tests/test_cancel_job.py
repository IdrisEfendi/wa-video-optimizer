import unittest
import warnings

warnings.simplefilter("ignore", ResourceWarning)

from fastapi.testclient import TestClient

from backend.main import app
from backend.services import job_service
from backend import settings


class CancelJobTest(unittest.TestCase):
    def test_cancel_queued_job_sets_cancel_requested(self):
        job_id = "job_cancel_test"
        job_service.save_job(
            {
                "job_id": job_id,
                "status": "queued",
                "stored_filename": "missing.mp4",
                "output_filename": None,
                "thumbnail_filename": None,
                "original": {"width": 320, "height": 180, "fps": 30, "duration": 1, "file_size": 1000},
                "expires_at": "2999-01-01T00:00:00+07:00",
            }
        )

        try:
            response = TestClient(app).post(f"/api/jobs/{job_id}/cancel")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.json()["status"], "cancel_requested")
            self.assertEqual(job_service.get_job(job_id)["status"], "cancel_requested")
        finally:
            (settings.JOB_DIR / f"{job_id}.json").unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
