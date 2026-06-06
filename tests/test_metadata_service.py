import tempfile
import unittest
from pathlib import Path

from backend.services import metadata_service


class MetadataServiceTest(unittest.TestCase):
    def test_empty_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "empty.mp4"
            path.write_bytes(b"")

            with self.assertRaises(metadata_service.InvalidVideoError):
                metadata_service.read_metadata(path)

    def test_fake_video_file_is_rejected(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "fake.mp4"
            path.write_bytes(b"not a real video")

            with self.assertRaises(metadata_service.InvalidVideoError):
                metadata_service.read_metadata(path)


if __name__ == "__main__":
    unittest.main()
