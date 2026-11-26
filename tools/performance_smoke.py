"""Read-only performance checks for a running Frigate Classic instance."""

import argparse
import concurrent.futures
import gzip
import json
import re
import statistics
import subprocess
import time
from pathlib import Path
from urllib.parse import quote
from urllib.request import Request, urlopen

PREFIX = "/perf/frigate"

# Run inside the container so the metrics come from its own cgroup.
CGROUP_SAMPLE = """
import json
import statistics
import sys
import time
from pathlib import Path
root = Path("/sys/fs/cgroup")
def counters(filename):
    return {k: int(v) for k, v in (line.split() for line in (root / filename).read_text().splitlines())}
start = time.monotonic()
initial = counters("cpu.stat")["usage_usec"]
anonymous, total = [], []
for _ in range(int(sys.argv[1])):
    time.sleep(1)
    anonymous.append(counters("memory.stat")["anon"])
    total.append(int((root / "memory.current").read_text()))
elapsed = time.monotonic() - start
print(json.dumps({
    "idle_cpu_percent": round((counters("cpu.stat")["usage_usec"] - initial) / elapsed / 10000, 2),
    "idle_anon_mib": round(statistics.median(anonymous) / 1048576, 2),
    "idle_memory_mib": round(statistics.median(total) / 1048576, 2),
}))
"""

SQLITE_CHECK = """
import json
import sqlite3
import sys
from pathlib import Path

path = Path(sys.argv[1]).resolve()
for descriptor in Path("/proc").glob("[0-9]*/fd/*"):
    try:
        target = descriptor.readlink()
    except OSError:
        continue
    if target == path:
        break
else:
    raise SystemExit(f"Configured database is not open in this container: {path}")

with sqlite3.connect(f"{path.as_uri()}?mode=ro", uri=True, timeout=2) as db:
    check = db.execute("PRAGMA quick_check(1)").fetchone()[0]
print(json.dumps({"database": str(path), "quick_check": check}))
"""


def fetch(base, path, headers=None):
    started = time.perf_counter()
    req = Request(
        base + path, headers={"Accept-Encoding": "identity", **(headers or {})}
    )
    with urlopen(req, timeout=12) as response:
        body = response.read()
        return body, response.headers, round((time.perf_counter() - started) * 1000, 2)


def check_database(base, container):
    config = json.loads(fetch(base, "/api/config")[0])
    path = config.get("database", {}).get("path")
    if not isinstance(path, str) or not Path(path).is_absolute():
        raise ValueError("Frigate did not report an absolute database path")
    output = subprocess.check_output(
        ["docker", "exec", container, "python3", "-c", SQLITE_CHECK, path],
        text=True,
        timeout=30,
    )
    return json.loads(output)


def check_static(base):
    document, _, _ = fetch(base, "/config")
    assets = re.findall(rb'(?:href|src)="(/assets/[^"]+\.(?:js|css))"', document)
    paths = ["/config", "/assets/yaml.worker.bundle.js"]
    for suffix in (b".js", b".css"):
        paths.append(next(path.decode() for path in assets if path.endswith(suffix)))

    sizes = {}
    for ingress in ("", PREFIX):
        headers = (
            {"X-Ingress-Path": ingress, "Via": "1.1 perf-proxy"} if ingress else {}
        )
        for path in paths:
            raw, _, _ = fetch(base, path, headers)
            packed, response, _ = fetch(
                base, path, {**headers, "Accept-Encoding": "gzip"}
            )
            assert response.get("Content-Encoding") == "gzip", (path, ingress)
            assert "Accept-Encoding" in response.get("Vary", ""), (path, ingress)
            assert gzip.decompress(packed) == raw, (path, ingress)
            if path == "/config":
                assert f'window.baseUrl="{ingress}/"'.encode() in raw
                assert f"{ingress}/assets/yaml.worker.bundle.js".encode() in raw
                assert b"/BASE_PATH/" not in raw
            if path.endswith("yaml.worker.bundle.js"):
                # The original regression transferred the full worker uncompressed.
                assert len(packed) <= 0.6 * len(raw), ingress
            sizes[f"{ingress or '/'} {path}"] = {
                "identity_bytes": len(raw),
                "gzip_bytes": len(packed),
            }
    return sizes


def check_api(base, samples):
    config = json.loads(fetch(base, "/api/config")[0])
    cameras = [name for name, cam in config["cameras"].items() if cam["enabled"]][:6]
    if not cameras:
        raise ValueError(
            "At least one enabled camera is required for the live smoke test"
        )

    def snapshot(cam):
        started = time.perf_counter()
        body, headers, _ = fetch(
            base, f"/api/{quote(cam, safe='')}/latest.webp?height=360"
        )
        finished = time.perf_counter()
        assert headers.get("Content-Type") == "image/webp", cam
        assert "no-store" in headers.get("Cache-Control", ""), cam
        assert body[:4] == b"RIFF" and body[8:12] == b"WEBP", cam
        return started, finished

    schema_times = [
        fetch(base, "/api/config/schema.json", {"X-Cache-Bypass": "1"})[2]
        for _ in range(samples)
    ]
    profiles, batches, in_flight = [], [], []
    with concurrent.futures.ThreadPoolExecutor(max_workers=len(cameras)) as pool:
        for _ in range(samples):
            start = time.perf_counter()
            frames = [pool.submit(snapshot, cam) for cam in cameras]
            # Give requests a head start and verify which were still in flight.
            time.sleep(0.01)
            profile_started = time.perf_counter()
            profiles.append(fetch(base, "/api/profile")[2])
            spans = [frame.result() for frame in frames]
            in_flight.append(
                sum(begin <= profile_started < end for begin, end in spans)
            )
            batches.append(round((time.perf_counter() - start) * 1000, 2))

    overlapped = [ms for ms, overlap in zip(profiles, in_flight) if overlap]
    metrics = {
        "profile_median_ms": round(statistics.median(profiles), 2),
        "snapshot_batch_median_ms": round(statistics.median(batches), 2),
        "schema_median_ms": round(statistics.median(schema_times), 2),
    }
    if overlapped:
        metrics["profile_with_snapshots_median_ms"] = round(
            statistics.median(overlapped), 2
        )
    return {
        "cameras": len(cameras),
        "metrics": metrics,
        "samples": {
            "profile_ms": profiles,
            "snapshots_in_flight_at_profile_start": in_flight,
            "snapshot_batch_ms": batches,
            "schema_ms": schema_times,
        },
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8972")
    parser.add_argument("--samples", type=int, default=7)
    parser.add_argument(
        "--container", help="Docker container to sample after the HTTP run"
    )
    parser.add_argument(
        "--database-only",
        action="store_true",
        help="Check the active SQLite database in the selected local container",
    )
    parser.add_argument("--idle-seconds", type=int, default=24)
    parser.add_argument(
        "--limits", type=Path, help="JSON map of optional upper bounds for metrics"
    )
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.samples < 1 or args.idle_seconds < 1:
        parser.error("Sample counts and duration must be positive")

    base = args.base_url.rstrip("/")
    if args.database_only:
        if not args.container or args.limits:
            parser.error("--database-only requires --container and no metric limits")
        result = check_database(base, args.container)
    else:
        result = check_api(base, args.samples)
        result["static"] = check_static(base)
    if args.container and not args.database_only:
        output = subprocess.check_output(
            [
                "docker",
                "exec",
                args.container,
                "python3",
                "-c",
                CGROUP_SAMPLE,
                str(args.idle_seconds),
            ],
            text=True,
        )
        result["metrics"].update(json.loads(output))

    serialized = json.dumps(result, indent=2) + "\n"
    if args.output:
        args.output.write_text(serialized)
    print(serialized, end="")

    if args.database_only and result["quick_check"] != "ok":
        raise SystemExit(1)

    if args.limits:
        for key, limit in json.loads(args.limits.read_text()).items():
            if key not in result["metrics"]:
                raise SystemExit(f"Metric was not measured: {key}")
            if result["metrics"][key] > limit:
                raise SystemExit(f"{key} exceeded {limit}: {result['metrics'][key]}")


if __name__ == "__main__":
    main()
