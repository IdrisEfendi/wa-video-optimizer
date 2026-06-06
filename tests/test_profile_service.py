import unittest

from backend.services import profile_service


class ProfileServiceTest(unittest.TestCase):
    def test_standard_estimate_downscales_4k_60fps(self):
        estimate = profile_service.estimate_settings(
            {
                "width": 3840,
                "height": 2160,
                "fps": 60,
                "duration": 10,
                "file_size": 100 * 1024 * 1024,
                "bitrate": 12_000_000,
            },
            "standard",
        )

        self.assertEqual(estimate["resolution"], "1920x1080")
        self.assertEqual(estimate["fps"], 30)
        self.assertEqual(estimate["crf"], 24)
        self.assertGreater(estimate["estimated_size"]["high_bytes"], 0)
        self.assertTrue(any("4K" in warning for warning in estimate["warnings"]))

    def test_story_estimate_targets_vertical_canvas(self):
        estimate = profile_service.estimate_settings(
            {
                "width": 1920,
                "height": 1080,
                "fps": 30,
                "duration": 15,
                "file_size": 20 * 1024 * 1024,
                "bitrate": 4_000_000,
            },
            "story",
        )

        self.assertEqual(estimate["resolution"], "1080x1920")
        self.assertTrue(any("9:16" in change for change in estimate["changes"]))


if __name__ == "__main__":
    unittest.main()
