# Frigate Classic

Build from the repository root. The image extends the pinned Frigate base and builds
the frontend from this checkout. Set the build argument `FRIGATE_BASE` to a
different upstream hardware image at the same Frigate version when appropriate.

```sh
docker build -f docker/classic/Dockerfile -t frigate-classic:0.18.3 .
```

Use Frigate's normal container mounts and configuration. For a development
instance, the example below binds the internal admin UI to localhost. Use the
authenticated port `8971` for deployments accessible from other machines.

```sh
docker run -d --restart unless-stopped --name frigate-classic \
  --shm-size 1024m -p 127.0.0.1:8972:5000 \
  -v "$PWD/config:/config" -v "$PWD/models:/models:ro" \
  -v "$PWD/media:/media/frigate" frigate-classic:0.18.3
```

## Measure detection quality on local recordings

Create a test manifest with one entry per clip. Use `tp` when the object is present
and `fp` when it is absent. A previous miss belongs in the `tp` group. Camera IDs
must match the supplied configuration, with explicit `detect.width` and
`detect.height` set. An optional `bounds` box limits scoring to a target in
detect-frame pixels. The detector still receives the full camera frames.

```json
[
  {"id": "person-missed", "camera": "front", "file": "person.mp4", "expected": "tp"},
  {"id": "person-false", "camera": "front", "file": "empty.mp4", "expected": "fp"}
]
```

Store the config, manifest, and clips in a private replay directory. Configure
the detector and its model as usual. Use a runnable backend on the Docker host.

```sh
docker run --rm --network none --entrypoint python3 \
  -v "$PWD/replay:/replay" -v "$PWD/models:/models:ro" frigate-classic:0.18.3 \
  -u /opt/frigate/tools/quality_replay.py \
  --config /replay/config.yml --manifest /replay/manifest.json \
  --output /replay/results.json --idle-scan 2 --trace
```

Repeat with `--idle-scan 0` or a second config and output path. To debug one
event, pass `--case person-missed`. The JSON reports peak raw model confidence,
peak object-tracker score, confirmation, frame count, and detector calls. With
`--trace` it also records boxes and scores at each relevant observation.

Replay feeds recorded frames through Frigate's native motion detector, region
selection, model preprocessing, Norfair tracker, and camera state. Each
clip starts with an empty camera region grid unless a saved grid is supplied
with `--grid`. The runner measures object confirmation before Review rules,
uses synchronous model calls, and replays a file without live frame drops.
Keep the footage and the optional grid identical for configuration comparisons.

`detect.idle_scan_interval` defaults to zero. A positive value runs one tile
after that many consecutive idle frames, rotating through up to four overlapping
tiles. Idle scanning is suppressed during motion calibration and PTZ movement
when autotracking reports it. Enable it per camera to control detector load.


ONNX CPU workers accept a `num_threads` setting. With two workers, use the same
model configuration for both. Measure processed frames and skipped frames in
System before increasing the scan rate or the number of detector workers.

## Control detection and recording from the configuration file

Set `FRIGATE_CONFIG_ONLY_CAMERA_CONTROLS=true` in the container environment
to lock runtime camera enablement, detection, motion, and recording controls.
Previously persisted overrides for these controls are ignored while locked.
Profiles can still change their other settings. Edit the mounted config file
and restart the container to change those enablement settings.

For faster idle Birdseye startup, `birdseye.idle_heartbeat_fps: 3` runs a
three-frame-per-second heartbeat for an empty composition with a connected
viewer. Birdseye's activity mode remains independently configurable.

## Performance regression checks

The performance suite uses request and byte budgets for the things the
application controls. It checks cold startup without using a millisecond
deadline for camera traffic or a machine-dependent render time.

From `web/`, use the installed Playwright Chromium:

```sh
npm run e2e:build
npm run e2e:perf
```

To use the assets of an already running Classic build, even when the npm
preview server is unavailable:

```sh
FRIGATE_PERF_URL=http://127.0.0.1:8972 npm run e2e:perf
```

These tests mock API and WebSocket responses, including on the second path.
Set `FRIGATE_PERF_BROWSER` to the executable path for an alternate Chromium
browser. The runner creates its own test context. The pull request workflow
runs these checks with strict browser errors enabled.

They enforce decoded JavaScript budgets and request boundaries for Cameras,
a single camera, Birdseye, Settings, Config, System, Review, Replay, and Events. The
Config test holds the Monaco download until it sees the YAML request.
The Events test covers tab persistence, no-clip fallback, and deferred video
and tracking requests.

From the repository root, run the backend guards in the Frigate Python
environment:

```sh
python3 -m unittest frigate.test.test_performance frigate.test.test_detection_evidence
```

With a matching local Classic image:

```sh
docker run --rm --network none --entrypoint python3 \
  -v "$PWD/frigate/test/test_performance.py:/opt/frigate/frigate/test/test_performance.py:ro" \
  frigate-classic:0.18.3-release \
  -m unittest frigate.test.test_performance frigate.test.test_detection_evidence
```

They exercise the bounded encoder pool without relying on a timing race,
schema serialization, plain frame rendering, Birdseye startup and idle frame
cadence, and the existing fresh-evidence and scan coverage regressions.

### Live measurements

Use a running Classic instance with an enabled camera and a recorded event:

```sh
# From web/
FRIGATE_PERF_URL=http://127.0.0.1:8972 FRIGATE_PERF_LIVE=1 npm run e2e:perf -- live.spec.ts

# From the repository root. Close monitoring tabs for the idle sample.
python3 tools/performance_smoke.py --container frigate-classic-0183 --output perf.json
```

The browser run records three first-frame measurements for each of Live,
Birdseye when enabled, and event playback. Set `FRIGATE_PERF_CAMERA` to
select a specific camera and `FRIGATE_PERF_EVENT_ID` to reuse a specific clip
across builds. Otherwise, the run selects a clip once and reuses it for every
sample. The report records the build, browser, selected inputs, and observed
player modes. Set `FRIGATE_PERF_FRAME_BUDGET_MS` to enforce a median
first-frame limit in your environment. The HTTP run checks gzip
payloads and path substitution with and without a proxy prefix and `Via`,
plus `no-store` for the latest camera images. It measures schema response
time, profile response time, and optional container CPU and memory. For each
profile request it records how many snapshot HTTP requests were still in
flight at its start. `profile_with_snapshots_median_ms` uses only samples
with observed client-side overlap. The backend unit test checks encoder
concurrency separately. A JSON `--limits` file can enforce host-specific
limits, for example `{"profile_with_snapshots_median_ms": 60, "idle_memory_mib": 4600}`.
The live runs issue reads only. Prefer an isolated instance for resource
comparisons, since camera activity changes independently of requests.

To check SQLite on the local Docker instance, use its API and container:

```sh
python3 tools/performance_smoke.py --database-only --container frigate-classic-0183
```

The check reads the configured database path from Frigate and verifies that
the container has it open before running SQLite's read-only `quick_check`.

### Replay regression budgets

For the saved camera archive, use the same manifest, time windows, and
camera settings as the reference run. Pass the previous result file and
choose how much extra detector work to allow:

```sh
# Add to the quality_replay.py command above.
--baseline /replay/reference.json --max-call-increase-percent 10
```

Replay checks the SHA-256 of the decoded pixels and timestamps, along with
camera, labels, frame count, dimensions, FPS, time window, and target bounds.
It also records the config fingerprint, detector/model, grid, seed, and
runner settings. Reports created before those fields were introduced must
be regenerated before comparison. For a deliberate setting change, repeat
`--allow-setting-change FIELD` for the expected differences. For example,
a new model configured in a different file can change `config_sha256` and
`model_hash`. Changes to the decoded input require a new baseline.

Replay fails when a previously correct event outcome regresses or when
detector calls exceed the chosen budget. Improvements on previously missed
cases are allowed.
Keep private footage, event manifests, reference scores and live reports
outside the source repository.
