---
id: updating
title: Updating
---

# Updating HeisenCam

The [development branch](https://github.com/kzkvv/heisencam/tree/dev) runs the 0.18.3 backend. Verified builds publish images for AMD64 and ARM64. System → General displays the build channel and commit. The `/api/version` response keeps the existing format for integrations.

## Before you begin

Record your current image digest, configuration file, model selection and volume locations. Back up the database using SQLite's backup operation, or stop the recorder before copying its database files. Test an upgrade against copies of both the configuration and the database before switching a recorder that holds important footage.

The archive build suppressed manual event deletion. On the current release, an administrator can delete events and their media even with capture controls locked. Assign review-only accounts to users who must preserve evidence. Verify access and a separate backup before switching.

## Updating with Docker

The example Compose file uses the `ghcr.io/kzkvv/heisencam:candidate-0.18.3` tag. Run these commands from its directory.

```sh
docker compose pull
docker compose up -d
docker compose ps
```

Check the camera wall, open a recent recording and inspect detector activity in System. To pin a build, set `HEISENCAM_IMAGE=ghcr.io/kzkvv/heisencam:sha-<full commit SHA>` in the demo's `.env` file before running Compose. A custom deployment can use that image reference directly in the service's `image` setting.

## Home Assistant

The [existing Home Assistant integration](../integrations/home-assistant.md) can connect to a HeisenCam server. The upstream Home Assistant app is a separate installation with its own update cycle. The Docker commands above update a separate HeisenCam server.

## Rolling back

Stop the updated recorder, restore the matching configuration and database backup, select the previous image digest, and start the recorder with its original volume mappings. Keep recordings captured since the backup available until you have verified your archive. The [migration and rollback notes](https://github.com/kzkvv/heisencam/blob/dev/docs/heisencam-compatibility.md#migration-and-rollback) describe the rehearsal on a 0.12.1 database copy.
