# Archived deployment

The application is upstream v0.12.1 at `367d7244d37f4e48ce1760b319c0fe141ab58711` with two byte-for-byte deployment overlays. The public dev tip `7b520e8a9d7c449f2546c854d5a3f6b278977b51` represents a different revision.

| File | SHA-256 |
| --- | --- |
| `frigate/comms/dispatcher.py` | `f662282810017af132e76a6ba1c4ebb8ab208a2a291b6a8d2e719c46a5af36fa` |
| `frigate/http.py` | `8a158a21bb63482aa7570299f4ed51d2aa45b7d448ed160e7e6fd1a2db7056c9` |

Build from this tag and check the historical behavior on an isolated machine.

```sh
docker build --platform linux/amd64 -f docker/legacy/Dockerfile -t heisencam-legacy .
docker run --rm --platform linux/amd64 --network none --entrypoint python3 \
  -e PYTHONPATH=/opt/frigate -v "$PWD/docker/legacy:/checks:ro" heisencam-legacy /checks/verify.py
```

The historical HTTP handlers return 200 with a disabled message. The dispatcher can acknowledge a requested state over MQTT even when the underlying switch stays on. Those details are part of the archive's compatibility contract.

## Backport to 0.12.1

Both fixes originate in HeisenCam commit `5e3c1d24c6fe09829263632798ef9777e9816e49`. They are adapted to the original tracker's data structures.

| Fix | Negative control at legacy-workaround-1 | Backport |
| --- | --- | --- |
| Reused stationary boxes carry no new detector evidence | Three cached frames promote a 90% observation | Track remains unconfirmed with one genuine observation |
| Rotate one independent tile after N idle frames | An interval of 2 produces only the nine startup calls in 17 frames | Nine startup calls and four distinct idle tiles |
| Default scan cost | Nine startup calls | Nine startup calls with the default interval of zero |

Set `detect.idle_scan_interval` per camera to opt in. Run both the archive check above and `/checks/test_backport.py -v` in the built image. The 0.12.1 tracker, startup scan and median initialization differ from 0.18.3, so scores and regions can differ across releases.
