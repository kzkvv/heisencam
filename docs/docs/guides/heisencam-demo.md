---
title: Try HeisenCam
description: Run six sample camera feeds, play their recordings and test detection settings.
---

import DemoLink from "@site/src/components/DemoLink";

The <DemoLink>browser demo</DemoLink> plays recorded street scenes from California and Calgary. Select a camera for playback, open Birdseye for a six-camera overview, or select a detection in Events. It works without an account.

## Run the full recorder

Run these commands on a machine with Git and Docker Compose installed.

```sh
git clone --depth 1 --branch dev https://github.com/kzkvv/heisencam.git
cd heisencam/examples/demo
docker compose up -d
```

Open [the local dashboard](http://127.0.0.1:8972/). If that port is busy, run `HEISENCAM_PORT=8974 docker compose up -d` and open port 8974 instead. The six inputs are bundled files. Detection runs locally on the CPU and each camera keeps one day of continuous recordings in Docker volumes.

Open **Events** after the detector has observed some activity. The Capture controls are locked to the configuration file in this example. Edit `config.yml` and restart the service to change them. Run `docker compose down` to stop the example and keep its volumes.

## Connect your cameras

Use the [camera setup guide](../frigate/camera_setup.md) to assign your camera's streams to detection and recording. Set [retention](../configuration/record.md) to fit your storage. The sample binds its administrator port to loopback. Use the [authenticated interface](../configuration/authentication.md) when other machines need access.

## Compare detection settings

Keep a set of labeled clips with people or cars and a second set of false alerts. Run the same clips before and after changing the model or `detect.idle_scan_interval`. The replay reports confirmed objects, detector calls and per-frame scores. See the [replay command and input format](https://github.com/kzkvv/heisencam/blob/dev/docker/classic/README.md#measure-detection-quality-on-local-recordings).

Run the [public replay fixtures](https://github.com/kzkvv/heisencam/tree/dev/examples/demo#public-detection-replay) to see a small baseline for people and cars.

The <DemoLink sources>demo sources and credits</DemoLink> identify each camera, its publisher and how the recording was prepared.
