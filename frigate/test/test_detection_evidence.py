"""Regression tests for detector evidence and idle coverage."""

import unittest
from types import SimpleNamespace

from frigate.config.camera.review import ReviewConfig
from frigate.track.tracked_object import TrackedObject
from frigate.video.detect import idle_scan_regions


class TestDetectionEvidence(unittest.TestCase):
    def setUp(self):
        self.initial = {
            "id": "test",
            "label": "person",
            "score": 0.9,
            "score_history": [0.55] * 5,
            "frame_time": 1.0,
            "start_time": 1.0,
            "motionless_count": 0,
            "position_changes": 0,
            "box": (1, 1, 40, 80),
            "centroid": (20, 40),
            "area": 3081,
            "ratio": 0.49,
            "region": (0, 0, 416, 416),
            "attributes": [],
        }
        model = SimpleNamespace(colormap={}, all_attribute_logos=[], attributes_map={})
        camera = SimpleNamespace(
            name="test",
            objects=SimpleNamespace(filters={"person": SimpleNamespace(threshold=0.7)}),
            detect=SimpleNamespace(
                stationary=SimpleNamespace(threshold=5), width=640, height=480
            ),
            zones={},
            review=ReviewConfig(),
        )
        self.obj = TrackedObject(model, camera, None, {}, self.initial.copy())

    def test_cached_observations_do_not_confirm_a_track(self):
        for frame in range(2, 8):
            self.obj.update(
                frame,
                {**self.initial, "frame_time": frame, "detector_evidence": False},
                False,
            )
        self.assertEqual(self.obj.score_history, [0.55] * 5)
        self.assertAlmostEqual(self.obj.top_score, 0.55)
        self.assertTrue(self.obj.false_positive)
        self.assertNotIn("detector_evidence", self.obj.to_dict())

    def test_fresh_observations_can_confirm_a_track(self):
        for frame in range(2, 8):
            self.obj.update(
                frame,
                {**self.initial, "frame_time": frame, "detector_evidence": True},
                False,
            )
        self.assertFalse(self.obj.false_positive)
        self.assertAlmostEqual(self.obj.top_score, 0.9)

    def test_missed_observation_still_counts_as_zero(self):
        self.obj.update(2.0, self.initial.copy(), False)
        self.assertEqual(self.obj.score_history[-1], 0.0)


class TestIdleScanRegions(unittest.TestCase):
    def test_tiles_cover_edges_and_overlap(self):
        for height, width in ((1080, 1920), (1944, 2592), (1920, 1080), (480, 640)):
            with self.subTest(height=height, width=width):
                tiles = idle_scan_regions((height, width), 416)
                self.assertLessEqual(len(tiles), 4)
                for x in (0, width // 2, width - 1):
                    for y in (0, height // 2, height - 1):
                        self.assertTrue(
                            any(
                                x0 <= x < x1 and y0 <= y < y1
                                for x0, y0, x1, y1 in tiles
                            ),
                            (x, y),
                        )
