---
id: index
title: HeisenCam
slug: /
---

HeisenCam is a local NVR derived from Frigate 0.18.3. The classic camera dashboard opens one object's recording in a single click. Review groups activity by time and camera, and History provides a recording timeline.

## Get started

Run the [two-camera Docker example](https://github.com/kzkvv/heisencam/tree/heisencam/0.18.3/examples/demo) to try the interface. For your own cameras, configure the FFmpeg inputs, storage, retention and detector for the host. Access to the internal administrator endpoint in the example is bound to localhost.

## Measure changes

Use the [local quality replay and performance checks](https://github.com/kzkvv/heisencam/blob/heisencam/0.18.3/docker/classic/README.md) to compare false alerts and misses on labelled clips. The reference chapters also cover the APIs, MQTT topics and integrations inherited from Frigate.
