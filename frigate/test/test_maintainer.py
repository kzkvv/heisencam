import datetime
import sys
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from peewee import SqliteDatabase

from frigate.models import ReviewSegment

# Mock complex imports before importing maintainer, saving originals so we can
# restore them after import and avoid polluting sys.modules for other tests.
_MOCKED_MODULES = [
    "frigate.comms.inter_process",
    "frigate.comms.detections_updater",
    "frigate.comms.recordings_updater",
    "frigate.config.camera.updater",
]
_originals = {name: sys.modules.get(name) for name in _MOCKED_MODULES}
for name in _MOCKED_MODULES:
    sys.modules[name] = MagicMock()

# Now import the class under test
from frigate.config import FrigateConfig, RecordConfig, RetainModeEnum  # noqa: E402
from frigate.record.maintainer import RecordingMaintainer  # noqa: E402

# Restore original modules (or remove mock if there was no original)
for name, orig in _originals.items():
    if orig is None:
        sys.modules.pop(name, None)
    else:
        sys.modules[name] = orig


class TestMaintainer(unittest.IsolatedAsyncioTestCase):
    async def test_move_files_survives_bad_filename(self):
        config = MagicMock(spec=FrigateConfig)
        config.cameras = {}
        stop_event = MagicMock()

        maintainer = RecordingMaintainer(config, stop_event)

        # We need to mock end_time_cache to avoid key errors if logic proceeds
        maintainer.end_time_cache = {}

        # Mock filesystem
        # One bad file, one good file
        files = ["bad_filename.mp4", "camera@20210101000000+0000.mp4"]

        with patch("os.listdir", return_value=files):
            with patch("os.path.isfile", return_value=True):
                with patch(
                    "frigate.record.maintainer.psutil.process_iter", return_value=[]
                ):
                    with patch("frigate.record.maintainer.logger.warning") as warn:
                        # Mock validate_and_move_segment to avoid further logic
                        maintainer.validate_and_move_segment = MagicMock()

                        try:
                            await maintainer.move_files()
                        except ValueError as e:
                            if "not enough values to unpack" in str(e):
                                self.fail("move_files() crashed on bad filename!")
                            raise e
                        except Exception:
                            # Ignore other errors (like DB connection) as we only care about the unpack crash
                            pass

                        # The bad filename is encountered in multiple loops, but should only warn once.
                        matching = [
                            c
                            for c in warn.call_args_list
                            if c.args
                            and isinstance(c.args[0], str)
                            and "Skipping unexpected files in cache" in c.args[0]
                        ]
                        self.assertEqual(
                            1,
                            len(matching),
                            f"Expected a single warning for unexpected files, got {len(matching)}",
                        )

    async def test_drops_quiet_segment_when_only_motion_retention(self):
        # Regression: when motion retention is enabled but a segment has no
        # motion and no review overlaps it, the segment must still be dropped.
        # Otherwise it sits in cache forever, accumulates, and triggers the
        # "Unable to keep up with recording segments in cache" warning every
        # ~10s as the overflow trim in move_files discards the oldest one.
        config = MagicMock(spec=FrigateConfig)

        camera_config = MagicMock()
        camera_config.record.enabled = True
        camera_config.record.continuous.days = 0
        camera_config.record.motion.days = 1
        camera_config.record.event_pre_capture = 5
        config.cameras = {"test_cam": camera_config}

        stop_event = MagicMock()
        maintainer = RecordingMaintainer(config, stop_event)

        now = datetime.datetime.now(datetime.UTC)
        start_time = now - datetime.timedelta(seconds=20)
        end_time = now - datetime.timedelta(seconds=10)
        cache_path = "/tmp/cache/test_cam@20260417150000+0000.mp4"

        maintainer.end_time_cache = {cache_path: (end_time, 10.0)}
        # Single processed frame well past end_time with no motion/objects.
        maintainer.object_recordings_info["test_cam"] = [(now.timestamp(), [], [], [])]
        maintainer.audio_recordings_info["test_cam"] = []

        maintainer.drop_segment = MagicMock()
        maintainer.recordings_publisher = MagicMock()

        result = await maintainer.validate_and_move_segment(
            "test_cam",
            reviews=[],
            recording={"start_time": start_time, "cache_path": cache_path},
        )

        self.assertIsNone(result)
        maintainer.drop_segment.assert_called_once_with(cache_path)

    async def test_defers_review_overlap_segment_until_metadata_catches_up(self):
        # Regression: a segment overlapping an active_objects review must not
        # be dropped while detection metadata lags behind the segment end,
        # the missing frames may hold the active objects (or continuous
        # retention would keep it anyway).
        config = MagicMock(spec=FrigateConfig)

        camera_config = MagicMock()
        camera_config.record.enabled = True
        camera_config.record.continuous.days = 7
        camera_config.record.motion.days = 0
        camera_config.record.alerts.retain.mode = RetainModeEnum.active_objects
        camera_config.record.get_review_pre_capture.return_value = 5
        camera_config.record.get_review_post_capture.return_value = 5
        config.cameras = {"test_cam": camera_config}

        stop_event = MagicMock()
        maintainer = RecordingMaintainer(config, stop_event)

        now = datetime.datetime.now(datetime.UTC)
        start_time = now - datetime.timedelta(seconds=20)
        end_time = now - datetime.timedelta(seconds=10)
        cache_path = "/tmp/cache/test_cam@20260417150000+0000.mp4"

        maintainer.end_time_cache = {cache_path: (end_time, 10.0)}
        # Metadata has only reached partway into the segment.
        maintainer.object_recordings_info["test_cam"] = [
            (end_time.timestamp() - 8, [], [], [])
        ]
        maintainer.audio_recordings_info["test_cam"] = []

        maintainer.drop_segment = MagicMock()
        maintainer.move_segment = AsyncMock(return_value=None)
        maintainer.recordings_publisher = MagicMock()

        review = MagicMock()
        review.severity = "alert"
        review.start_time = start_time.timestamp() - 30
        review.end_time = None

        result = await maintainer.validate_and_move_segment(
            "test_cam",
            reviews=[review],
            recording={"start_time": start_time, "cache_path": cache_path},
        )

        self.assertIsNone(result)
        maintainer.drop_segment.assert_not_called()
        maintainer.move_segment.assert_not_awaited()

        # Once metadata passes the segment end, continuous retention keeps it.
        maintainer.object_recordings_info["test_cam"].append(
            (now.timestamp(), [], [], [])
        )

        await maintainer.validate_and_move_segment(
            "test_cam",
            reviews=[review],
            recording={"start_time": start_time, "cache_path": cache_path},
        )

        maintainer.drop_segment.assert_not_called()
        maintainer.move_segment.assert_awaited_once()

    async def test_closed_review_keeps_post_capture_candidates(self):
        camera = "test_cam"
        config = MagicMock(spec=FrigateConfig)
        config.cameras = {
            camera: SimpleNamespace(
                record=RecordConfig.model_validate(
                    {"enabled": True, "alerts": {"post_capture": 60}}
                )
            )
        }
        # Full discovery can import the maintainer before this module's mocks.
        with (
            patch("frigate.record.maintainer.InterProcessRequestor"),
            patch("frigate.record.maintainer.RecordingsDataPublisher"),
        ):
            maintainer = RecordingMaintainer(config, MagicMock())
        maintainer.validate_and_move_segment = AsyncMock(return_value=None)
        start = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        review_end = start.timestamp() - 40

        with (
            SqliteDatabase(":memory:") as db,
            db.bind_ctx([ReviewSegment]),
            tempfile.TemporaryDirectory() as cache_dir,
        ):
            db.create_tables([ReviewSegment])
            ReviewSegment.create(
                id="review",
                camera=camera,
                start_time=review_end - 10,
                end_time=review_end,
                severity="alert",
                thumb_path="",
                data={},
            )
            timestamp = start.strftime("%Y%m%d%H%M%S%z")
            Path(cache_dir, f"{camera}@{timestamp}.mp4").touch()
            with (
                patch("frigate.record.maintainer.CACHE_DIR", cache_dir),
                patch("frigate.record.maintainer.psutil.process_iter", return_value=[]),
            ):
                await maintainer.move_files()

            reviews = maintainer.validate_and_move_segment.call_args.args[1]
            self.assertEqual([review.end_time for review in reviews], [review_end])

    async def test_overlapping_alert_keeps_quiet_segment(self):
        camera = "test_cam"
        config = MagicMock(spec=FrigateConfig)
        config.cameras = {
            camera: SimpleNamespace(
                record=RecordConfig.model_validate(
                    {
                        "enabled": True,
                        "continuous": {"days": 0},
                        "motion": {"days": 0},
                        "alerts": {"retain": {"mode": "all"}},
                        "detections": {"retain": {"mode": "motion"}},
                    }
                )
            )
        }
        maintainer = RecordingMaintainer(config, MagicMock())
        start = datetime.datetime(2026, 1, 1, tzinfo=datetime.UTC)
        end = start + datetime.timedelta(seconds=10)
        path = "/tmp/quiet-segment.mp4"
        maintainer.end_time_cache[path] = (end, 10.0)
        maintainer.object_recordings_info[camera] = [(end.timestamp(), [], [], [])]
        maintainer.move_segment = AsyncMock()
        maintainer.drop_segment = MagicMock()

        await maintainer.validate_and_move_segment(
            camera,
            reviews=[
                SimpleNamespace(
                    severity="detection", start_time=start.timestamp(), end_time=None
                ),
                SimpleNamespace(
                    severity="alert", start_time=start.timestamp() + 1, end_time=None
                ),
            ],
            recording={"start_time": start, "cache_path": path},
        )

        maintainer.move_segment.assert_awaited_once()
        maintainer.drop_segment.assert_not_called()

    async def test_expire_stale_recordings_info_drops_only_absent_cameras(self):
        config = MagicMock(spec=FrigateConfig)
        config.cameras = {}
        stop_event = MagicMock()
        maintainer = RecordingMaintainer(config, stop_event)

        now = datetime.datetime.now().timestamp()
        ancient = now - 86400
        recent = now - 1

        maintainer.object_recordings_info["present_cam"] = [(ancient, [], [], [])]
        maintainer.audio_recordings_info["present_cam"] = [(ancient, 0, [])]

        maintainer.object_recordings_info["absent_cam"] = [
            (ancient, [], [], []),
            (recent, [], [], []),
        ]
        maintainer.audio_recordings_info["absent_cam"] = [
            (ancient, 0, []),
            (recent, 0, []),
        ]

        grouped_recordings = {"present_cam": [{"start_time": ancient}]}

        maintainer._expire_stale_recordings_info(grouped_recordings)

        self.assertEqual(
            maintainer.object_recordings_info["present_cam"], [(ancient, [], [], [])]
        )
        self.assertEqual(
            maintainer.audio_recordings_info["present_cam"], [(ancient, 0, [])]
        )

        self.assertEqual(
            maintainer.object_recordings_info["absent_cam"], [(recent, [], [], [])]
        )
        self.assertEqual(
            maintainer.audio_recordings_info["absent_cam"], [(recent, 0, [])]
        )


if __name__ == "__main__":
    unittest.main()
