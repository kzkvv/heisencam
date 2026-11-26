# Six-camera demonstration

Open the [browser demo](https://kzkvv.github.io/heisencam/demo/) to play sample cameras, Birdseye and recorded person or car detections. The [installation guide](https://kzkvv.github.io/heisencam/docs/guides/heisencam-demo/) also explains how to run the full recorder.

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

The [source list](https://kzkvv.github.io/heisencam/demo/#sources) links each camera to its publisher. The browser demo serves bundled recordings and stills from its own site. Its Events view uses a selection of native HeisenCam snapshots from these six inputs. Each snapshot was matched to the decoded frames of its source loop to locate the corresponding playback time. The displayed percentage is the detector score stored with the snapshot.
