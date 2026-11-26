"""Exercise the backported tracker and region scheduler with deterministic input."""
import queue
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from frigate import video
from frigate.config import FrigateConfig
from frigate.object_processing import TrackedObject
from frigate.objects import ObjectTracker


def config():
    return FrigateConfig.parse_obj({
        "mqtt": {"enabled": False},
        "cameras": {"demo": {
            "ffmpeg": {"inputs": [{"path": "/demo.mp4", "roles": ["detect"]}]},
            "detect": {"enabled": True, "width": 640, "height": 480, "fps": 5},
        }},
    }).runtime_config


class QualityBackportTest(unittest.TestCase):
    def test_cached_stationary_predictions_do_not_raise_confidence(self):
        cfg = config()
        cam = cfg.cameras["demo"]
        detector = ObjectTracker(cam.detect)
        detection = ("person", 0.90, (30, 50, 90, 180), 7800, 60/130, (0, 0, 320, 320))
        detector.match_and_update(10.0, [detection])
        target = next(iter(detector.tracked_objects.values()))
        tracked = TrackedObject("demo", cfg.model.colormap, cam, {}, dict(target))
        for stamp in (10.2, 10.4, 10.6):
            detector.update_frame_times(stamp)
            tracked.update(stamp, dict(target))
        self.assertTrue(tracked.false_positive)
        self.assertEqual(tracked.score_history, [0.9])

    def scan(self, interval):
        cfg = config()
        cam = cfg.cameras["demo"]
        # Exercise the scheduler on the original image too, before its schema
        # knows about the setting.
        object.__setattr__(cam.detect, "idle_scan_interval", interval)
        times = queue.Queue()
        for n in range(17):
            times.put(float(n + 1))
        frames = Mock()
        frames.get.return_value = np.zeros((720, 640), np.uint8)
        motion = Mock()
        motion.detect.return_value = []
        with patch.object(video, "detect", return_value=[]) as infer:
            video.process_frames(
                "demo", times, cam.frame_shape, cfg.model, cam.detect, frames,
                motion, Mock(), ObjectTracker(cam.detect), queue.Queue(),
                {name: SimpleNamespace(value=0.0) for name in
                 ("process_fps", "detection_fps", "detection_frame")},
                cam.objects.track, cam.objects.filters, SimpleNamespace(value=True),
                SimpleNamespace(value=True), threading.Event(), exit_on_empty=True,
            )
        return [call.args[4] for call in infer.call_args_list]

    def test_idle_scan_rotates_four_tiles_after_startup(self):
        regions = self.scan(2)
        self.assertEqual(len(regions), 13)
        self.assertEqual(len(set(regions[9:])), 4)

    def test_default_scan_cost_is_unchanged(self):
        self.assertEqual(len(self.scan(0)), 9)


if __name__ == "__main__":
    unittest.main()
