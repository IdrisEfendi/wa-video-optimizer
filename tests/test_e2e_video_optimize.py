import shutil
import subprocess
import tempfile
import unittest
import warnings
from pathlib import Path

warnings.simplefilter("ignore", ResourceWarning)

from fastapi.testclient import TestClient

from backend.main import app
from backend.services import job_service, storage_service


@unittest.skipUnless(shutil.which("ffmpeg"), "ffmpeg is required for e2e video test")
class VideoOptimizeE2ETest(unittest.TestCase):
    def test_upload_optimize_compare_download(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            sample = Path(temp_dir) / "sample.mp4"
            subprocess.run(
                [
                    "ffmpeg",
                    "-y",
                    "-hide_banner",
                    "-loglevel",
                    "error",
                    "-f",
                    "lavfi",
                    "-i",
                    "testsrc=size=320x180:rate=30",
                    "-f",
                    "lavfi",
                    "-i",
                    "sine=frequency=1000:sample_rate=44100",
                    "-t",
                    "1",
                    "-c:v",
                    "libx264",
                    "-pix_fmt",
                    "yuv420p",
                    "-c:a",
                    "aac",
                    str(sample),
                ],
                check=True,
            )

            client = TestClient(app)
            with sample.open("rb") as handle:
                upload = client.post("/api/upload", files={"video": ("sample.mp4", handle, "video/mp4")})
            self.assertEqual(upload.status_code, 200)
            job_id = upload.json()["job_id"]

            try:
                optimize = client.post("/api/optimize", json={"job_id": job_id, "profile": "standard"})
                self.assertEqual(optimize.status_code, 200)

                status = client.get(f"/api/optimize/{job_id}/status")
                self.assertEqual(status.status_code, 200)
                self.assertEqual(status.json()["status"], "completed")

                compare = client.get(f"/api/compare/{job_id}")
                self.assertEqual(compare.status_code, 200)
                self.assertEqual(compare.json()["optimized"]["video_codec"], "h264")

                download = client.get(f"/api/download/{job_id}")
                self.assertEqual(download.status_code, 200)
                self.assertGreater(len(download.content), 0)
            finally:
                try:
                    storage_service.delete_job_files(job_service.get_job(job_id))
                except FileNotFoundError:
                    pass


if __name__ == "__main__":
    unittest.main()
