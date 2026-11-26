"""Measure Frigate's tracked-object scores by replaying labelled local clips."""

import argparse
import hashlib
import json
import math
import os
import queue
import random
import shutil
import struct
import subprocess
from collections import defaultdict
from importlib import import_module
from pathlib import Path
from time import perf_counter
from types import SimpleNamespace
from unittest.mock import patch

import cv2
import numpy as np
import onnxruntime as ort
from ruamel.yaml import YAML

from frigate.camera import PTZMetrics
from frigate.camera.state import CameraState
from frigate.config import FrigateConfig
from frigate.detectors import detection_runners
from frigate.motion.improved_motion import ImprovedMotionDetector
from frigate.object_detection.base import LocalObjectDetector
from frigate.track.norfair_tracker import NorfairTracker
from frigate.util.object import create_empty_regions_grid

video = import_module("frigate.video.detect")

OFFLINE_INPUT = "/dev/null"
PROFILE_FIELDS = (
    "config_sha256",
    "detector",
    "model_hash",
    "grid_sha256",
    "idle_scan",
    "seed",
    "onnx_threads",
)
INPUT_FIELDS = ("camera", "label", "expected", "frames", "input")


def file_sha256(path):
    if path is None:
        return None
    with Path(path).open("rb") as source:
        return hashlib.file_digest(source, "sha256").hexdigest()


def load_config(path, camera_names, idle_scan):
    with path.open() as stream:
        source = YAML(typ="safe").load(stream)
    source["mqtt"] = {"enabled": False}
    source["cameras"] = {
        name: {
            **source["cameras"][name],
            "enabled": True,
            "ffmpeg": {"inputs": [{"path": OFFLINE_INPUT, "roles": ["detect"]}]},
        }
        for name in camera_names
    }
    for name, camera in source["cameras"].items():
        detect = {**source.get("detect", {}), **camera.get("detect", {})}
        if not (detect.get("width") and detect.get("height")):
            raise ValueError(f"{name} needs explicit detect width and height")
    config = FrigateConfig.parse_object(source)
    for camera in config.cameras.values():
        camera.detect.enabled = True
        if idle_scan is not None:
            if hasattr(camera.detect, "idle_scan_interval"):
                camera.detect.idle_scan_interval = idle_scan
            elif idle_scan:
                raise ValueError("This Frigate image has no idle scan setting")
    return config


def clip_parts(case):
    if "file" in case:
        return [{"file": case["file"], "start": case.get("start", 1.0)}]

    # Stay within the contiguous recording sequence closest to the labelled frame.
    groups = []
    for part in sorted(case["parts"], key=lambda item: item["start"]):
        if not groups or part["start"] - groups[-1][-1]["start"] > 13:
            groups.append([])
        groups[-1].append(part)
    if not groups:
        raise ValueError(f"{case['id']} has no video parts")
    anchor = case["anchor"]
    return min(
        groups,
        key=lambda group: max(
            group[0]["start"] - anchor, 0, anchor - group[-1]["start"] - 10
        ),
    )


def decoded_frames(case, root, settings, ffmpeg):
    width, height, fps = settings.width, settings.height, settings.fps
    frame_size = width * height * 3 // 2
    window = case.get("window", [0, math.inf])
    last_stamp = 0
    for part in clip_parts(case):
        command = [
            ffmpeg,
            "-nostdin",
            "-loglevel",
            "error",
            "-threads",
            "2",
            "-i",
            str(root / part["file"]),
            "-an",
            "-vf",
            f"fps={fps},scale={width}:{height}",
            "-pix_fmt",
            "yuv420p",
            "-threads",
            "1",
            "-f",
            "rawvideo",
            "pipe:1",
        ]
        with subprocess.Popen(command, stdout=subprocess.PIPE) as process:
            index = 0
            try:
                while payload := process.stdout.read(frame_size):
                    if len(payload) != frame_size:
                        raise RuntimeError(f"Incomplete frame in {part['file']}")
                    stamp = round(part["start"] + index / fps, 6)
                    index += 1
                    if window[0] <= stamp <= window[1] and stamp > last_stamp:
                        last_stamp = stamp
                        yield (
                            stamp,
                            np.frombuffer(payload, dtype=np.uint8).reshape(
                                (height * 3 // 2, width)
                            ),
                        )
            finally:
                process.stdout.close()
            if process.wait() != 0:
                raise RuntimeError(f"FFmpeg failed for {part['file']}")


class ReplayFrames:
    """Provide one decoded frame to the production tracker and state updater."""

    def __init__(self, frames):
        self.frames = iter(frames)
        self.frame = None
        self.frame_name = None
        self.first = None
        self.last = None
        self.count = 0
        self.digest = hashlib.sha256()

    def dequeue(self, *_args):
        item = next(self.frames, None)
        if item is None:
            raise queue.Empty
        stamp, self.frame = item
        # Include the timestamp as well as the decoded YUV pixels given to Frigate.
        self.digest.update(struct.pack("!d", stamp))
        self.digest.update(self.frame)
        self.frame_name = f"replay-{stamp}"
        if self.first is None:
            self.first = stamp
        self.last = stamp
        self.count += 1
        return self.frame_name, stamp

    def get(self, name, _shape):
        return self.frame if name == self.frame_name else None

    def close(self, _name):
        pass


def matches_target(box, bounds):
    if bounds is None:
        return True
    x0, y0, x1, y1 = box
    a0, b0, a1, b1 = bounds
    width, height = a1 - a0, b1 - b0
    area = (x1 - x0) * (y1 - y0)
    bound_area = width * height
    intersection = max(0, min(x1, a1) - max(x0, a0)) * max(0, min(y1, b1) - max(y0, b0))
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    return intersection / max(1, area + bound_area - intersection) >= 0.15 or (
        a0 - width * 0.15 <= cx <= a1 + width * 0.15
        and b0 - height * 0.15 <= cy <= b1 + height * 0.15
        and intersection >= 0.35 * min(area, bound_area)
        and area >= 0.20 * bound_area
    )


def run_case(case, config, detector, root, ffmpeg, include_trace, region_grid):
    camera = config.cameras[case["camera"]]
    bounds = case.get("bounds")
    label = case.get("label", "person")
    if label not in camera.objects.track:
        raise ValueError(
            f"{case['id']} expects {label}, which {camera.name} does not track"
        )
    ptz = PTZMetrics(autotracker_enabled=False)
    source = ReplayFrames(decoded_frames(case, root, camera.detect, ffmpeg))
    tracker = NorfairTracker(camera, ptz)
    tracker.frame_manager = source
    state = CameraState(camera.name, config, source, None)
    motion = ImprovedMotionDetector(
        camera.frame_shape, camera.motion, camera.detect.fps, ptz_metrics=ptz
    )
    clock = SimpleNamespace(value=0)
    metrics = SimpleNamespace(
        detection_frame=clock,
        process_fps=SimpleNamespace(value=0),
        detection_fps=SimpleNamespace(value=0),
    )
    calls = 0
    raw_peak = None
    track_peak = None
    first_confirmed = None
    raw_trace = []
    track_trace = defaultdict(list)
    original_detect = video.detect

    def trace_detect(*args, **kwargs):
        nonlocal raw_peak, calls
        calls += 1
        rows = original_detect(*args, **kwargs)
        for found, score, box, _area, _ratio, region in rows:
            if found == label and matches_target(box, bounds):
                raw_peak = max(raw_peak or 0, score)
                if include_trace:
                    raw_trace.append(
                        {"t": clock.value, "score": score, "box": box, "region": region}
                    )
        return rows

    def consume(record):
        nonlocal track_peak, first_confirmed
        _, frame_name, stamp, detections, motion_boxes, regions = record
        state.update(frame_name, stamp, detections, motion_boxes, regions)
        for key, obj in state.tracked_objects.items():
            data = obj.obj_data
            if data["label"] != label or not matches_target(data["box"], bounds):
                continue
            track_peak = max(track_peak or 0, obj.top_score)
            if not obj.false_positive and first_confirmed is None:
                first_confirmed = stamp
            if include_trace:
                track_trace[key].append(
                    {
                        "t": stamp,
                        "top_score": obj.top_score,
                        "computed_score": obj.computed_score,
                        "raw": data["score"],
                        "confirmed": not obj.false_positive,
                        "fresh": data.get("detector_evidence", True)
                        and data["frame_time"] == stamp,
                        "box": data["box"],
                    }
                )

    started = perf_counter()
    with (
        patch.object(video, "detect", trace_detect),
        patch.object(
            video,
            "CameraConfigUpdateSubscriber",
            return_value=SimpleNamespace(check_for_updates=dict, stop=lambda: None),
        ),
    ):
        video.process_frames(
            requestor=SimpleNamespace(stop=lambda: None),
            frame_queue=SimpleNamespace(get=source.dequeue),
            frame_shape=camera.frame_shape,
            model_config=config.model,
            camera_config=camera,
            frame_manager=source,
            motion_detector=motion,
            object_detector=detector,
            object_tracker=tracker,
            detected_objects_queue=SimpleNamespace(full=lambda: False, put=consume),
            camera_metrics=metrics,
            stop_event=SimpleNamespace(is_set=lambda: False),
            ptz_metrics=ptz,
            region_grid=region_grid,
            exit_on_empty=True,
        )
    if not source.count:
        raise ValueError(f"{case['id']} has zero frames in the selected window")

    result = {
        "id": case["id"],
        "expected": case["expected"],
        "camera": camera.name,
        "label": label,
        "threshold": camera.objects.filters[label].threshold,
        "frames": source.count,
        "input": {
            "decoded_sha256": source.digest.hexdigest(),
            "size": [camera.detect.width, camera.detect.height],
            "fps": camera.detect.fps,
            "window": case.get("window"),
            "bounds": bounds,
        },
        "first": source.first,
        "last": source.last,
        "detector_calls": calls,
        "raw_peak": raw_peak,
        "track_peak": track_peak,
        "confirmed": first_confirmed is not None,
        "first_confirmed": first_confirmed,
        "elapsed_seconds": round(perf_counter() - started, 3),
    }
    if include_trace:
        result.update(raw_trace=raw_trace, tracks=track_trace)
    return result


def json_default(value):
    if isinstance(value, np.generic):
        return value.item()
    raise TypeError(f"Cannot serialize {type(value)}")


def check_baseline(results, baseline, max_call_increase_percent, allowed_changes=()):
    """Guard detection quality and work on the same labelled footage."""
    previous = {row["id"]: row for row in baseline}
    current = {row["id"]: row for row in results}
    if (
        len(previous) != len(baseline)
        or len(current) != len(results)
        or previous.keys() != current.keys()
    ):
        raise SystemExit(
            "Replay baseline and candidate must contain the same unique cases"
        )

    regressions = []
    for key, old in previous.items():
        new = current[key]
        if not old.get("input") or not old.get("profile"):
            raise SystemExit("Baseline has no replay provenance. Regenerate it first.")
        for field in INPUT_FIELDS:
            if old.get(field) != new.get(field):
                raise SystemExit(f"Case {key} has different replay input: {field}")
        for field in PROFILE_FIELDS:
            if field not in old["profile"] or field not in new["profile"]:
                raise SystemExit(
                    f"Case {key} has an incomplete replay profile: {field}"
                )
            if old["profile"][field] == new["profile"][field]:
                continue
            if field not in allowed_changes:
                raise SystemExit(f"Case {key} has different replay settings: {field}")
        wanted = old["expected"] == "tp"
        if old["confirmed"] == wanted and new["confirmed"] != wanted:
            regressions.append(
                f"{key}: unexpected {'confirmation' if new['confirmed'] else 'miss'}"
            )

    old_calls = sum(row["detector_calls"] for row in baseline)
    new_calls = sum(row["detector_calls"] for row in results)
    print(f"Detector calls: {old_calls} -> {new_calls}", flush=True)
    if new_calls > old_calls * (1 + max_call_increase_percent / 100):
        regressions.append(
            f"detector calls exceeded the {max_call_increase_percent:g}% increase budget"
        )
    if regressions:
        raise SystemExit("Replay regressions:\n" + "\n".join(regressions))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--manifest", required=True, type=Path)
    parser.add_argument("--root", type=Path, help="Base directory for media paths")
    parser.add_argument(
        "--bounds", type=Path, help="Optional JSON mapping IDs to boxes"
    )
    parser.add_argument(
        "--grid", type=Path, help="Optional JSON mapping cameras to grids"
    )
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument(
        "--baseline",
        type=Path,
        help="Compare against a previous replay of the same cases",
    )
    parser.add_argument("--max-call-increase-percent", type=float, default=10)
    parser.add_argument(
        "--allow-setting-change",
        action="append",
        default=[],
        choices=PROFILE_FIELDS,
        help="Allow a specific profile difference for an intentional comparison",
    )
    parser.add_argument("--detector", help="Detector name in the config")
    parser.add_argument("--idle-scan", type=int)
    parser.add_argument("--case", action="append", help="Limit to an ID or ID suffix")
    parser.add_argument("--trace", action="store_true")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--onnx-threads", type=int, default=2)
    parser.add_argument("--ffmpeg", default=shutil.which("ffmpeg"))
    args = parser.parse_args()
    if args.max_call_increase_percent < 0 or not math.isfinite(
        args.max_call_increase_percent
    ):
        parser.error("--max-call-increase-percent must be finite and nonnegative")
    if args.baseline and args.baseline.resolve() == args.output.resolve():
        parser.error("--baseline and --output must be different files")
    baseline = json.loads(args.baseline.read_text()) if args.baseline else None
    if args.idle_scan is not None and args.idle_scan < 0:
        parser.error("--idle-scan must be nonnegative")

    cases = json.loads(args.manifest.read_text())
    if args.case:
        cases = [
            case
            for case in cases
            if case["id"] in args.case or case["id"].rsplit("-", 1)[-1] in args.case
        ]
    if not cases or any(case["expected"] not in ("tp", "fp") for case in cases):
        parser.error("Provide selected cases labelled tp or fp")
    bounds = json.loads(args.bounds.read_text()) if args.bounds else {}
    grids = json.loads(args.grid.read_text()) if args.grid else {}
    for case in cases:
        if case["id"] in bounds:
            case["bounds"] = bounds[case["id"]]
    config = load_config(
        args.config, {case["camera"] for case in cases}, args.idle_scan
    )
    detector_config = config.detectors[args.detector or next(iter(config.detectors))]
    if args.onnx_threads < 1:
        parser.error("--onnx-threads must be positive")
    original_options = detection_runners.get_ort_session_options

    def session_options(model_type):
        options = original_options(model_type) or ort.SessionOptions()
        options.intra_op_num_threads = args.onnx_threads
        options.add_session_config_entry("session.intra_op.allow_spinning", "0")
        return options

    with patch.object(detection_runners, "get_ort_session_options", session_options):
        detector = LocalObjectDetector(
            detector_config, detector_config.model.labelmap_path
        )
    detector.labels = detector_config.model.merged_labelmap
    profile = {
        "config_sha256": file_sha256(args.config),
        "detector": detector_config.type,
        "model_hash": detector_config.model.model_hash,
        "grid_sha256": file_sha256(args.grid),
        "idle_scan": args.idle_scan,
        "seed": args.seed,
        "onnx_threads": args.onnx_threads,
    }
    cv2.setNumThreads(1)
    root = args.root or args.manifest.parent
    ffmpeg = args.ffmpeg or os.path.join(config.ffmpeg.ffmpeg_path, "bin", "ffmpeg")

    results = []
    args.output.parent.mkdir(parents=True, exist_ok=True)
    checkpoint = args.output.with_suffix(f".{os.getpid()}.tmp")
    for case in cases:
        random.seed(args.seed)
        grid = grids.get(case["camera"]) or create_empty_regions_grid()
        result = run_case(case, config, detector, root, ffmpeg, args.trace, grid)
        result["profile"] = profile
        results.append(result)
        checkpoint.write_text(
            json.dumps(results, indent=2, default=json_default) + "\n"
        )
        checkpoint.replace(args.output)
        print(
            f"{result['id']} {result['expected']} confirmed={result['confirmed']} "
            f"raw={result['raw_peak']} track={result['track_peak']} "
            f"calls={result['detector_calls']} elapsed={result['elapsed_seconds']}s",
            flush=True,
        )

    if baseline is not None:
        check_baseline(
            results, baseline, args.max_call_increase_percent, args.allow_setting_change
        )


if __name__ == "__main__":
    main()
