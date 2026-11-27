<p align="center"><img src="web/images/branding/favicon.svg" width="76" height="76" alt="HeisenCam lens"></p>

# HeisenCam

> **I saw who knocked**

HeisenCam is a local network video recorder built on [Frigate 0.18.3](https://github.com/blakeblackshear/frigate/tree/v0.18.3). We bring the classic camera dashboard and single-click event playback to the current backend, alongside Review, History and Explore.

Our name nods to Walter White's line in *Cornered*. Camera footage once helped our founder identify people leaving drug drops. We kept the camera's answer as our tagline. The graphite lens and its faceted blue reflection are original HeisenCam artwork. [Background on the scene at ACMI](https://www.acmi.net.au/stories-and-ideas/breaking-bad-i-am/)

## Run the candidate

```sh
git clone --depth 1 --branch heisencam/0.18.3 https://github.com/kzkvv/heisencam.git
cd heisencam/examples/demo
docker compose up -d
```

Open [the local dashboard](http://127.0.0.1:8972). The example replays six public traffic-camera samples from California and Calgary. Its recordings and database use separate Docker volumes. The candidate publishes AMD64 and ARM64 images to `ghcr.io/kzkvv/heisencam`. For repeatable deployment, use the tag `sha-<full candidate commit SHA>` or its OCI digest.

## Versioning

HeisenCam uses calendar versions in the form `YYYY.M.N`. The month is unpadded, and the release counter starts at `1` each month. For example, `2026.11.1` and `2026.11.2` are the first two releases of November 2026. The release notes describe API changes and any migration steps.

Set the next release number in [VERSION](VERSION) and wait for CI to build the merged commit on `dev`. Then use a matching Git tag such as `v2026.11.1` for the GitHub release. The release workflow publishes the corresponding image as `ghcr.io/kzkvv/heisencam:2026.11.1` and updates `stable` for stable releases. To publish a prerelease, use a suffix such as `v2026.11.1-beta.1` and mark it as a prerelease on GitHub.

## What changes

- **Review footage** from a classic camera grid and play a tracked object's clip inline. Existing camera groups can be hidden per user.
- **Tune confirmation** using fresh detector evidence and an optional `detect.idle_scan_interval` per camera. Replay labelled recordings and compare confirmed tracks, scores and inference calls before choosing a setting.
- **Keep capture running** with `FRIGATE_CONFIG_ONLY_CAMERA_CONTROLS=true`. The file sets camera, motion, recording and detection enablement.
- **Load on demand** with deferred views, gzip after ingress path substitution and a bounded worker pool for dashboard snapshots.

Configuration keys, `FRIGATE_*` environment variables, MQTT topics, API routes and container storage paths follow Frigate conventions. The default detector and any additional hardware dependencies depend on your configuration and chosen base image.

[Browser demo](https://docs.heisen.cam/demo/) · [Documentation](https://docs.heisen.cam/) · [Docker demo and camera credits](examples/demo/README.md) · [Build and benchmark instructions](docker/classic/README.md) · [Archive, backport and rollback](docs/heisencam-compatibility.md)

HeisenCam is an independent derivative. Frigate and Frigate+ are trademarks of Frigate, Inc. The upstream code and copyright notices are retained. [MIT license](LICENSE) · [Upstream trademark policy](TRADEMARK.md)
