"""Regression checks for recorder readiness and retained camera controls."""

import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from frigate.api.app import _camera_controls_conflict, readiness
from frigate.api.media import _preview_size
from frigate.app import FrigateApp
from frigate.util.object import reduce_with_cached_detections


class TestReviewFixes(unittest.TestCase):
    def test_ready_requires_live_workers_and_a_fresh_frame(self):
        worker = Mock()
        worker.is_alive.return_value = True
        config = SimpleNamespace(
            safe_mode=False,
            cameras={
                "sample": SimpleNamespace(
                    enabled=True, ffmpeg=SimpleNamespace(retry_interval=10)
                )
            },
        )
        processor = Mock()
        request = SimpleNamespace(
            app=SimpleNamespace(
                frigate_config=config,
                state=SimpleNamespace(capture_workers=(worker,)),
                detected_frames_processor=processor,
            )
        )
        processor.get_current_frame_time.return_value = 0
        self.assertEqual(readiness(request).status_code, 503)
        processor.get_current_frame_time.return_value = time.time()
        self.assertEqual(readiness(request).status_code, 200)
        worker.is_alive.return_value = False
        self.assertEqual(readiness(request).status_code, 503)

    def test_corrupt_database_is_rejected_before_maintenance(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "recorder.db"
            path.write_bytes(b"not a SQLite database")
            app = SimpleNamespace(
                config=SimpleNamespace(database=SimpleNamespace(path=str(path)))
            )
            with self.assertRaisesRegex(RuntimeError, "known-good backup"):
                FrigateApp.init_database(app)

    def test_new_observation_wins_over_a_stationary_box(self):
        region = (0, 0, 640, 640)
        box = (320, 200, 420, 480)
        cached = ("person", 0.91, box, 28000, 0.35, region)
        fresh = ("person", 0.76, box, 28000, 0.35, region)
        unmatched = ("person", 0.80, (20, 40, 120, 320), 28000, 0.35, region)
        result = reduce_with_cached_detections(
            (1080, 1920), [cached, unmatched, fresh], {id(cached), id(unmatched)}
        )
        self.assertEqual(result, [fresh, unmatched])

    def test_preview_limits_pixels_even_on_wide_cameras(self):
        frame = np.empty((480, 1920, 3), dtype=np.uint8)
        self.assertIsNone(_preview_size(frame, 4096))
        self.assertEqual(_preview_size(frame, 360), (1440, 360))

    @patch("frigate.api.app.CAMERA_CONTROLS_LOCKED", True)
    def test_capture_lock_uses_effective_existing_camera_settings(self):
        original = """mqtt:
  enabled: false
cameras:
  sample:
    ffmpeg:
      inputs:
        - path: /demo/sample.mp4
          roles: [detect]
"""
        explicit = original.replace("  sample:\n", "  sample:\n    enabled: true\n")
        added = explicit + explicit[explicit.index("  sample:") :].replace(
            "sample:", "new_camera:", 1
        )
        disabled = explicit.replace("enabled: true", "enabled: false")
        self.assertIsNone(_camera_controls_conflict(original, explicit))
        self.assertIsNone(_camera_controls_conflict(original, added))
        self.assertEqual(_camera_controls_conflict(original, disabled).status_code, 403)
