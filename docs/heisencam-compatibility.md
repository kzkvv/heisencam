# HeisenCam candidate and compatibility checks

The candidate is based on upstream Frigate `v0.18.3` at `a19e23ae2dd3dd1082bf82a0ad5d2b62a5813676`. The classic interface and detection changes have a separate commit history on `heisencam/0.18.3`. Build from that branch or pull the image tagged `sha-<40-character commit SHA>`. Inspect `org.opencontainers.image.revision` on the image to identify the source revision.

## What the legacy archive contains

The archived installation uses upstream **v0.12.1** at `367d7244d37f4e48ce1760b319c0fe141ab58711`. Its two bind-mounted Python files were stored together in deployment source revision `925fd8028d23765deda4bc2f2e7a6df5602a2416`. Their SHA-256 hashes were checked against the running deployment's mount sources. The public fork's 2023 dev tip `7b520e8a9d7c449f2546c854d5a3f6b278977b51` describes a different tree.

The annotated tag [legacy-workaround-1](https://github.com/kzkvv/heisencam/tree/legacy-workaround-1) points at `cadc36c4f53ec595b551d24434410fad98bdebd4`. Build instructions and behavioral probes are under `docker/legacy` on that tag. The [0.12.1 backport](https://github.com/kzkvv/heisencam/tree/backport/0.12.1) preserves both overlays and adapts fresh detector evidence and the opt-in idle scan from `5e3c1d24c6fe09829263632798ef9777e9816e49`. Its three regression tests include controls that fail on the archive.

| Legacy behavior | Candidate behavior |
| --- | --- |
| MQTT detect, motion and recording commands acknowledge the request without changing the underlying switch | Set `FRIGATE_CONFIG_ONLY_CAMERA_CONTROLS=true` for file-controlled enablement. The dispatcher ignores locked commands and the HTTP API rejects them with 403. |
| Snapshot toggles and remote restart are suppressed | Snapshot and restart operations retain their upstream role and command semantics. The capture lock covers camera, motion, detect and recording enablement. |
| Raw config and saving config return a disabled message | Native roles protect administrative config routes. The capture lock rejects changes to protected enablement values while allowing other settings to be edited. |
| The event deletion handler returns a response without deleting media or the database row | Authorized event deletion is real in 0.18.3. A deployment that requires immutable evidence needs separate access controls and a retention policy. |

The Python package, storage paths, environment prefix, MQTT default prefix, API routes and upstream version format remain compatible. The product name, UI, manifests, icons and OCI metadata identify HeisenCam. Frigate+ and third-party integrations retain their own names.

## Quality replay

The old archive and the candidate were replayed locally on the same private labelled recordings with matched camera-specific windows and scoring bounds. The archive used its packaged CPU MobileDet model on the AMD64 image under emulation. The ARM64 candidate used YOLOv8n at 416 pixels with two ONNX CPU threads, confidence threshold 0.70, idle intervals of one or two frames according to camera. These are configuration-level results. They include differences in model, tracking and region selection.

| Matched person tracks | Archived 0.12.1 | Candidate |
| --- | ---: | ---: |
| Confirmed on eight positive windows | 7/8 | 8/8 |
| Confirmed on nine negative windows | 1/9 | 0/9 |
| Detector calls across the 17 windows | 2,388 | 1,931 |
| Confirmed on two held-out positive windows | 2/2 | 2/2 |
| Confirmed on two held-out negative windows | 0/2 | 0/2 |

The supplied benchmark accepts your own media and labels. Keep the input fingerprint, seed, model and region-grid initialization with a comparison. See [the benchmark guide](../docker/classic/README.md).

## Migration and rollback

Stop writers or take an online SQLite backup in the same operating system that owns the live database. Save the matching config, model selection, image digest and media volume mapping. Keep an independent copy for the trial. For Docker Desktop, put SQLite on a Linux Docker volume.

1. Verify SQLite integrity and inventory event and recording IDs on the snapshot.
2. Run the candidate's migrations against a copy. Migrate and validate a copy of the config. Verify integrity and compare the sets of IDs.
3. To roll back, stop the candidate, restore the original snapshot and config, and start the matching old image. Evaluate recordings made since the snapshot separately before changing a production deployment.

A local rehearsal used a consistent 0.12.1 database snapshot and a credential-sanitized copy of its six-camera configuration. The migration advanced from 12 to 35 applied migrations. All 5,327 event IDs and 682,715 recording IDs matched before and after. The archived snapshot retained its original checksum. Source recordings, local config and private camera imagery are outside the public example.

## Candidate CI

Only pushes to the named candidate branch publish candidate images. Pull requests run the web checks with a read-only token. Native AMD64 and ARM64 jobs test the image and publish architecture-specific SHA tags to `ghcr.io/kzkvv/heisencam`. A final job assembles the SHA and candidate manifests and checks the running image. Archive/backport pushes and the annotated legacy tag do not match the upstream dev/master build trigger. Upstream release publishing requires a separate release event or dispatch.
