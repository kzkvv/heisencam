# Six-camera demonstration

Open the [browser demo](https://docs.heisen.cam/demo/) to play sample cameras, Birdseye and recorded person or car detections. The [installation guide](https://docs.heisen.cam/guides/heisencam-demo/) also explains how to run the full recorder.

Run `docker compose up -d` in this directory and open `http://127.0.0.1:8972`. Set `HEISENCAM_PORT` to choose another port and `HEISENCAM_IMAGE` to pin a candidate SHA or digest. Use `docker compose down` to stop the example and keep its volumes.

Six simulated inputs loop the included 16-second H.264 files. Three are continuous camera excerpts, and three are time-lapses assembled from eight distinct municipal images held for two seconds each. All six sources were collected on November 26, 2026. The CPU detector tracks people and cars at a configured two frames per second per camera. The example keeps one day of continuous recordings. The database and recordings have separate Docker volumes.

The internal administrator interface is bound to loopback. For network access, configure native authentication and use the authenticated port 8971.

## Camera credits

| Demo view | Original camera | Media |
| --- | --- | --- |
| 40th Street crossing | Caltrans District 4, Emeryville, SR-123 at 40th Street, west-facing | Video |
| Downtown skywalk | City of Calgary, 5 Avenue / 5 Street SW, camera 123 | Time-lapse |
| Bay Bridge tower | Caltrans District 4, I-80, Bay Bridge SAS Tower East, TVD32 | Video |
| 12 Avenue corner | City of Calgary, 12 Avenue / 5 Street SW, camera 77 | Time-lapse |
| Crenshaw Boulevard | Caltrans District 7, Torrance, SR-1 at Crenshaw Boulevard, CCTV 220 | Video |
| 9 Avenue crossing | City of Calgary, 9 Avenue / 5 Street SW, camera 130 | Time-lapse |

California video is from the California Department of Transportation's public traffic-camera service. The original camera imprints are preserved. [Caltrans camera catalog](https://cwwp2.dot.ca.gov/closed-circuit-television-cameras.html) · [Caltrans Conditions of Use](https://dot.ca.gov/conditions-of-use)

Contains information licensed under the Open Government Licence – City of Calgary. [Traffic Cameras dataset](https://data.calgary.ca/Transportation-Transit/Traffic-Cameras/k7p9-kppz) · [City of Calgary licence](https://data.calgary.ca/stories/s/Open-Calgary-Terms-of-Use/u45n-7awa)

The [source list](https://docs.heisen.cam/demo/sources/) links each camera to its publisher. The browser demo runs the HeisenCam interface with bundled recordings and stills. Its Events view uses a selection of native HeisenCam snapshots from these six inputs. Each snapshot was matched to the decoded frames of its source loop to locate the corresponding playback time. The displayed percentage is the detector score stored with the snapshot.

## Reproduce the media

The camera catalog records source endpoints, acquisition method, dimensions and SHA-256 digests of the files used here. Collection date is known for all six feeds. The collection did not record exact UTC start times. For new captures, record the UTC time at the start of each HLS excerpt and at each JPEG retrieval. Store the timestamps with the source ID and the output hash.

1. From each Caltrans HLS feed take a 16-second excerpt. Encode H.264 with `yuv420p`, remove audio, and place the MP4 metadata at the start of the file (`-movflags +faststart`).
2. Collect eight distinct JPEGs per Calgary camera. Hold each for two seconds and encode to the same 16-second format. Preserve the publisher's imprint.
3. Take posters at 4.2 seconds and resize to a width of 640 pixels. For example, `ffmpeg -ss 4.2 -i camera.mp4 -frames:v 1 -vf scale=640:-2 poster.webp`. Create Birdseye by scaling, tiling and composing the same six 16-second inputs.
4. Loop the inputs through the Docker example. Find snapshots from confirmed person and car events, match each snapshot to the closest visual frame in its source video, and update the Events array in `site/demo/catalog.json` with the stored score and playback offset. Inspect each match and retain the camera credits.

## Public detection replay

The [replay manifest](replay/manifest.json) labels four clips with a person or car and adds two target labels for a moving synthetic test pattern with no people or cars. The examples are small regression fixtures. The positives can include a detector miss, and the negative control is synthetic.

From the root with a verified candidate image, run:

```sh
mkdir -p replay-results
docker run --rm --network none --entrypoint python3   -v "$PWD/examples/demo:/sample:ro" -v "$PWD/replay-results:/results"   ghcr.io/kzkvv/heisencam:candidate-0.18.3 /opt/frigate/tools/quality_replay.py   --config /sample/config.yml --manifest /sample/replay/manifest.json   --root /sample --idle-scan 2 --output /results/public.json
```

The [recorded CPU baseline](replay/baseline-cpu.json) confirmed three of four positive cases. The Torrance car reached a 72.7% model score and a 68.4% tracker score, below the configured 70% confirmation threshold. The two synthetic negative runs each made 29 detector calls and produced no tracked person or car. Compare this report using the same model and replay input. The provider list describes the initialized runtime. An ONNX provider list can include a fallback provider and does not identify how every operator ran.
