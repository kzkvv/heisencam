---
id: index
title: HeisenCam
slug: /
---

HeisenCam is a local network video recorder built on Frigate 0.18.3. Open a camera from the classic dashboard, play a tracked object's recording in Events, or use History to find the minute you need.

## Get started

- [Open the browser demo](https://kzkvv.github.io/heisencam/demo/) to explore six public street cameras and play recorded detections.
- [Run the same six sources in Docker](../guides/heisencam-demo.md) to try the full recorder with local detection and recording.
- [Configure your first camera](./camera_setup.md) and [choose a detector](../configuration/object_detectors.md) for your hardware.

## Measure changes

Use [quality replay](../guides/heisencam-demo.md#compare-detection-settings) to compare settings on the same labeled clips. The reference also covers [recording retention](../configuration/record.md), [MQTT](../integrations/mqtt.md) and the [HTTP API](./integrations/api/frigate-http-api/).
