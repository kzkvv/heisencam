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
