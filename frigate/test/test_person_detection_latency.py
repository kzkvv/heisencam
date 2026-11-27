"""Regression tests for timely person review and bounded calibration scans."""

import unittest
from queue import Queue
from types import SimpleNamespace
from typing import Any
from unittest.mock import Mock, patch

import numpy as np

from frigate.camera import PTZMetrics
from frigate.camera.state import CameraState
from frigate.config import FrigateConfig
from frigate.detectors.detector_config import ModelConfig
from frigate.events.maintainer import EventProcessor
from frigate.events.types import EventStateEnum, EventTypeEnum
from frigate.models import Event
from frigate.review.maintainer import ActiveObjects
from frigate.track.norfair_tracker import NorfairTracker
from frigate.track.object_processing import TrackedObjectProcessor
from frigate.util.image import SharedMemoryFrameManager
from frigate.util.object import create_empty_regions_grid, create_tensor_input
from frigate.video.detect import process_frames

Box = tuple[int, int, int, int]
Detection = tuple[str, float, Box, int, float, Box]
PERSON_PATH = ((260, 150, 300, 250), (272, 150, 312, 250), (284, 150, 324, 250))


def person_detection(box: Box, score: float, region: Box) -> Detection:
    """Return a detector result in camera coordinates."""
    width, height = box[2] - box[0], box[3] - box[1]
    return ("person", score, box, width * height, width / height, region)


class TestPersonDetectionLatency(unittest.TestCase):
    def setUp(self) -> None:
        self.config = FrigateConfig.parse_object(
            {
                "mqtt": {"enabled": False},
                "ffmpeg": {"hwaccel_args": []},
                "objects": {
                    "track": ["person"],
                    "filters": {"person": {"min_score": 0.5, "threshold": 0.7}},
                },
                "motion": {"enabled": True},
                "record": {"enabled": True},
                "snapshots": {"enabled": False},
                "review": {
                    "alerts": {"labels": ["person"]},
                    "detections": {"enabled": False},
                },
                "cameras": {
                    "entry": {
                        "mqtt": {"enabled": False},
                        "ffmpeg": {
                            "inputs": [
                                {"path": "/dev/null", "roles": ["detect", "record"]}
                            ]
                        },
                        "detect": {
                            "enabled": True,
                            "width": 640,
                            "height": 480,
                            "fps": 5,
                            "min_initialized": 2,
                            "idle_scan_interval": 0,
                        },
                    }
                },
            }
        )
        self.camera = self.config.cameras["entry"]
        self.frames = Mock(spec=SharedMemoryFrameManager)
        self.frames.get.return_value = np.zeros(
            self.camera.frame_shape_yuv, dtype=np.uint8
        )
        self.ptz = PTZMetrics(autotracker_enabled=False)
        self.tracker = NorfairTracker(self.camera, self.ptz)
        self.tracker.frame_manager = self.frames
        self.state = CameraState(self.camera.name, self.config, self.frames, Mock())
        self.review_frames: list[int] = []
        self.model_box_frames: set[int] = set()

    def _timestamp(self, frame: int) -> float:
        return 100 + frame / self.camera.detect.fps

    def _frame_number(self, timestamp: float) -> int:
        return round((timestamp - 100) * self.camera.detect.fps)

    def _update_review(
        self,
        frame_name: str,
        timestamp: float,
        tracks: dict[str, dict[str, Any]],
        motion: list[Box],
        regions: list[Box],
    ) -> None:
        self.state.update(frame_name, timestamp, tracks, motion, regions)
        objects = [obj.to_dict() for obj in self.state.tracked_objects.values()]
        if ActiveObjects(timestamp, self.camera, objects).has_active_objects():
            self.review_frames.append(self._frame_number(timestamp))

    def _track_frame(self, index: int, box: Box | None, score: float = 0.9) -> None:
        name, timestamp = str(index), self._timestamp(index)
        detections = [person_detection(box, score, (0, 0, 416, 416))] if box else []
        self.tracker.match_and_update(name, timestamp, detections)
        tracks = {
            key: {**obj, "attributes": []}
            for key, obj in self.tracker.tracked_objects.items()
        }
        self._update_review(name, timestamp, tracks, [], [])

    def test_short_moving_person_reaches_review_before_leaving(self) -> None:
        # Register the real callbacks without starting worker threads or IPC.
        processor = TrackedObjectProcessor.__new__(TrackedObjectProcessor)
        processor.config = self.config
        processor.frame_manager = self.frames
        processor.ptz_autotracker_thread = Mock()
        processor.dispatcher = Mock()
        processor.requestor = Mock()
        event_sender = Mock()
        processor.event_sender = event_sender
        processor.camera_states = {}
        processor.camera_activity = {}
        processor.create_camera_state(self.camera.name)
        self.state = processor.camera_states[self.camera.name]

        for index, (box, score) in enumerate(
            zip(PERSON_PATH, (0.51, 0.73, 0.96), strict=True), 1
        ):
            self._track_frame(index, box, score)
        self._track_frame(4, None)

        self.assertEqual(self.review_frames, [3])
        messages = [
            call.args[0]
            for call in event_sender.publish.call_args_list
            if int(call.args[0][3]) <= len(PERSON_PATH)
        ]
        self.assertEqual(
            [message[:4] for message in messages],
            [
                (
                    EventTypeEnum.tracked_object,
                    EventStateEnum.start,
                    self.camera.name,
                    "3",
                ),
                (
                    EventTypeEnum.tracked_object,
                    EventStateEnum.update,
                    self.camera.name,
                    "3",
                ),
            ],
        )
        start, update = (message[-1] for message in messages)
        self.assertEqual(start["id"], update["id"])
        self.assertFalse(update["false_positive"])
        self.assertTrue(update["has_clip"])
        # Duplicating the last score would increase the published median.
        self.assertAlmostEqual(update["computed_score"], 0.73)

        writer = EventProcessor.__new__(EventProcessor)
        writer.config = self.config
        writer.events_in_process = {start["id"]: start}
        with patch.object(Event, "insert") as insert:
            writer.handle_object_detection(
                EventStateEnum.update, self.camera.name, update
            )
        insert.return_value.on_conflict.return_value.execute.assert_called_once_with()
        stored = insert.call_args.args[0]
        self.assertTrue(stored[Event.has_clip])
        self.assertGreaterEqual(stored[Event.start_time], self._timestamp(1))
        self.assertLessEqual(
            stored[Event.start_time], self._timestamp(len(PERSON_PATH))
        )

    def test_weak_moving_person_does_not_trigger_review(self) -> None:
        # Include an update after registration while the person is still visible.
        for index, box in enumerate((*PERSON_PATH, (296, 150, 336, 250)), 1):
            self._track_frame(index, box, score=0.55)

        self.assertEqual(len(self.state.tracked_objects), 1)
        self.assertTrue(next(iter(self.state.tracked_objects.values())).false_positive)
        self.assertEqual(self.review_frames, [])

    def test_box_resizing_without_displacement_does_not_trigger_review(self) -> None:
        for index, box in enumerate(
            ((260, 150, 300, 250), (256, 137, 304, 250), (252, 124, 308, 250)), 1
        ):
            self._track_frame(index, box)
        self._track_frame(4, None)

        self.assertEqual(len(self.state.tracked_objects), 1)
        self.assertFalse(next(iter(self.state.tracked_objects.values())).false_positive)
        self.assertEqual(self.review_frames, [])

    def _run_camera(
        self,
        calibrating: list[bool],
        visible: tuple[Box, ...] = (),
        *,
        model_scores: dict[int, float] | None = None,
    ) -> list[tuple[int, Box]]:
        """Feed marked frames and recognize their boxes after real cropping."""
        scores = model_scores or {}
        frame_queue = Queue()
        detected_frames = Queue()
        for index in range(1, len(calibrating) + 1):
            frame_queue.put((str(index), self._timestamp(index)))

        blank = np.full(self.camera.frame_shape_yuv, 128, dtype=np.uint8)
        blank[: self.camera.frame_shape[0]] = 16
        marked_frames = {}
        for index, (x0, y0, x1, y1) in enumerate(visible, 1):
            frame = blank.copy()
            frame[y0:y1, x0:x1] = 235
            marked_frames[str(index)] = frame
        self.frames.get.side_effect = lambda name, _shape: marked_frames.get(
            name, blank
        )

        metrics = SimpleNamespace(
            detection_frame=SimpleNamespace(value=0.0),
            process_fps=SimpleNamespace(value=0.0),
            detection_fps=SimpleNamespace(value=0.0),
        )
        motion = Mock()
        motion.detect.return_value = []
        motion.is_calibrating.side_effect = lambda: calibrating[
            self._frame_number(metrics.detection_frame.value) - 1
        ]
        calls: list[tuple[int, Box]] = []
        active_region: Box | None = None

        def prepare_input(
            frame: np.ndarray, model_config: ModelConfig, region: Box
        ) -> np.ndarray:
            nonlocal active_region
            active_region = region
            return create_tensor_input(frame, model_config, region)

        def infer(tensor: np.ndarray) -> list[tuple[str, float, tuple[float, ...]]]:
            index = self._frame_number(metrics.detection_frame.value)
            assert active_region is not None
            calls.append((index, active_region))
            y, x = np.nonzero(tensor[0, :, :, 0] > 127)
            if not x.size:
                return []
            _, height, width, _ = tensor.shape
            box = (
                y.min() / height,
                x.min() / width,
                (y.max() + 1) / height,
                (x.max() + 1) / width,
            )
            self.model_box_frames.add(index)
            return [("person", scores.get(index, 0.9), box)]

        detector = Mock()
        detector.detect.side_effect = infer
        with (
            patch("frigate.video.detect.CameraConfigUpdateSubscriber") as subscribe,
            patch("frigate.video.detect.create_tensor_input", new=prepare_input),
        ):
            subscribe.return_value.check_for_updates.return_value = {}
            process_frames(
                requestor=Mock(),
                frame_queue=frame_queue,
                frame_shape=self.camera.frame_shape,
                model_config=self.config.model,
                camera_config=self.camera,
                frame_manager=self.frames,
                motion_detector=motion,
                object_detector=detector,
                object_tracker=self.tracker,
                detected_objects_queue=detected_frames,
                camera_metrics=metrics,
                stop_event=SimpleNamespace(is_set=lambda: False),
                ptz_metrics=self.ptz,
                region_grid=create_empty_regions_grid(),
                exit_on_empty=True,
            )
        while not detected_frames.empty():
            self._update_review(*detected_frames.get_nowait()[1:])
        return calls

    def test_short_pass_reaches_review_while_motion_is_calibrating(self) -> None:
        calls = self._run_camera([True] * 4, PERSON_PATH)

        self.assertEqual(self.review_frames, [3])
        # A single tracking region should not trigger a second, fallback scan.
        self.assertEqual(len(calls), len({frame for frame, _ in calls}))

    def test_scan_respects_the_camera_minimum_score_before_tracking(self) -> None:
        self.camera.objects.filters["person"].min_score = 0.65
        self.camera.detect.idle_scan_interval = 1
        self._run_camera([False] * 4, PERSON_PATH, model_scores={1: 0.60})

        self.assertEqual(self.model_box_frames, {1, 2, 3})
        self.assertFalse(self.state.tracked_objects)
        self.assertEqual(self.review_frames, [])

    def test_configured_idle_scan_resumes_after_calibration(self) -> None:
        self.camera.detect.idle_scan_interval = 2
        calls = self._run_camera([True] * 4 + [False] * 4)

        self.assertEqual([frame for frame, _ in calls if frame > 4], [6, 8])

    def test_calibration_scan_waits_for_ptz_motion_to_stop(self) -> None:
        self.camera.detect.idle_scan_interval = 2
        self.ptz.autotracker_enabled.value = True
        self.ptz.start_time.value = self._timestamp(0)
        self.ptz.stop_time.value = self._timestamp(10)
        with patch(
            "frigate.ptz.autotrack.SharedMemoryFrameManager", return_value=self.frames
        ):
            # A reported stop resets the motion baseline on the first stationary frame.
            calls = self._run_camera([True] * 10 + [False] * 4)

        self.assertEqual([frame for frame, _ in calls], [12, 14])

    def test_calibration_search_covers_the_view_within_its_budget(self) -> None:
        calls = self._run_camera([True] * 16 + [False] * 4 + [True] * 16)
        self.assertFalse(any(17 <= frame <= 20 for frame, _ in calls))
        for first, last in ((1, 16), (21, 36)):
            with self.subTest(calibration_started_on=first):
                observed = [(i, region) for i, region in calls if first <= i <= last]
                # At most two passes over four tiles, with one extra call per frame.
                self.assertLessEqual(len(observed), 8)
                self.assertEqual(len(observed), len({i for i, _ in observed}))
                covered = np.zeros(self.camera.frame_shape, dtype=bool)
                for _, (x0, y0, x1, y1) in observed:
                    covered[max(0, y0) : max(0, y1), max(0, x0) : max(0, x1)] = True
                self.assertEqual(np.count_nonzero(~covered), 0)
