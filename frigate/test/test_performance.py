"""Deterministic guards for concurrency, startup latency and repeated work."""

import asyncio
import threading
import time
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

import numpy as np

from frigate.api import app, media
from frigate.camera.state import CameraState
from frigate.output import birdseye


class TestFrameRequestPerformance(unittest.IsolatedAsyncioTestCase):
    async def test_snapshot_batch_yields_to_api_and_caps_encoder_workers(self):
        loop = asyncio.get_running_loop()
        api_thread = threading.get_ident()
        release = threading.Event()
        three_started = asyncio.Event()
        lock = threading.Lock()
        active = 0
        peak = 0

        def render(*args):
            nonlocal active, peak
            self.assertNotEqual(threading.get_ident(), api_thread)
            with lock:
                active += 1
                peak = max(peak, active)
                if active == 3:
                    loop.call_soon_threadsafe(three_started.set)
            try:
                self.assertTrue(release.wait(timeout=10))
                return media.Response(content=b"frame")
            finally:
                with lock:
                    active -= 1

        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace()))
        with patch.object(media, "_render_latest_frame", side_effect=render):
            frames = [
                asyncio.create_task(media.latest_frame(request, f"camera_{i}", "webp"))
                for i in range(6)
            ]
            try:
                await asyncio.wait_for(three_started.wait(), timeout=5)
                # The API loop must answer this while every encoder is held.
                self.assertEqual(str(app.version()), app.VERSION)
                self.assertTrue(all(not frame.done() for frame in frames))
                self.assertEqual(request.app.state.latest_frame_workers.total_tokens, 3)
            finally:
                release.set()
                responses = await asyncio.gather(*frames, return_exceptions=True)

        self.assertEqual(peak, 3)
        for response in responses:
            self.assertIsInstance(response, media.Response)
            self.assertEqual(response.body, b"frame")


class TestPreviewPerformance(unittest.TestCase):
    def test_plain_frames_skip_serializing_track_annotations(self):
        tracked = Mock()
        state = SimpleNamespace(
            current_frame_lock=threading.Lock(),
            _current_frame=np.zeros((6, 4), dtype=np.uint8),
            current_frame_time=100,
            tracked_objects={"object": tracked},
            motion_boxes=[],
            regions=[],
        )

        frame = CameraState.get_current_frame(state)

        self.assertEqual(frame.shape, (4, 4, 3))
        tracked.to_dict.assert_not_called()

    def test_latest_preview_uses_new_frame_and_is_not_cacheable(self):
        processor = Mock()
        processor.get_current_frame_time.return_value = time.time()
        processor.get_current_frame.side_effect = [
            np.zeros((8, 8, 3), dtype=np.uint8),
            np.full((8, 8, 3), 200, dtype=np.uint8),
        ]
        request = SimpleNamespace(
            app=SimpleNamespace(
                detected_frames_processor=processor,
                frigate_config=SimpleNamespace(
                    cameras={
                        "front": SimpleNamespace(
                            ffmpeg=SimpleNamespace(retry_interval=10)
                        )
                    }
                ),
            )
        )

        responses = [
            media._render_latest_frame(
                request,
                "front",
                media.Extension("webp"),
                media.MediaLatestFrameQueryParams(),
            )
            for _ in range(2)
        ]

        for result in responses:
            self.assertEqual(result.headers["cache-control"], "no-store")
            self.assertEqual(result.media_type, "image/webp")
        self.assertNotEqual(responses[0].body, responses[1].body)


class TestSchemaPerformance(unittest.TestCase):
    def test_schema_is_serialized_once_per_process(self):
        app._config_schema_bytes.cache_clear()
        self.addCleanup(app._config_schema_bytes.cache_clear)

        with patch.object(
            app, "get_config_schema", return_value={"type": "object"}
        ) as schema:
            first = app.config_schema()
            second = app.config_schema()

        self.assertEqual(first.body, second.body)
        self.assertEqual(first.headers["content-type"], "application/json")
        schema.assert_called_once_with(app.FrigateConfig)


class TestBirdseyeStartupPerformance(unittest.TestCase):
    def test_birdseye_muxer_limits_wait_for_a_keyframe(self):
        with patch.object(birdseye.sp, "Popen") as popen:
            birdseye.FFMpegConverter(
                SimpleNamespace(ffmpeg_path="ffmpeg"),
                Mock(),
                Mock(),
                640,
                480,
                640,
                480,
                8,
            )

        command = popen.call_args.args[0]
        self.assertLessEqual(int(command[command.index("-g") + 1]), 4)
        self.assertEqual(command[command.index("-muxdelay") + 1], "0")
        self.assertEqual(command[command.index("-flush_packets") + 1], "1")

    def test_idle_heartbeat_respects_its_frame_budget(self):
        send = Mock()
        view = SimpleNamespace(
            birdseye_manager=SimpleNamespace(
                update=Mock(return_value=(False, False)),
                camera_layout=[],
                last_output_time=0.0,
            ),
            _idle_interval=1 / 3,
            _Birdseye__send_new_frame=send,
        )
        frame = np.zeros((6, 4), dtype=np.uint8)

        with patch.object(birdseye.datetime, "datetime") as clock:
            for now in (100.0, 100.1, 100.2, 100.35, 100.45, 100.7):
                clock.now.return_value.timestamp.return_value = now
                birdseye.Birdseye.write_data(view, "front_door", [], [], now, frame)

        self.assertEqual(send.call_count, 3)
