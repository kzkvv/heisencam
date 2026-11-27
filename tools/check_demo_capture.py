"""Check that the six-camera Docker sample captures and publishes recordings."""

import argparse
import json
import time
from urllib.error import HTTPError
from urllib.parse import quote, urljoin, urlsplit

from performance_smoke import check_api, fetch


def check_recordings(base: str, cameras: list[str], started: float) -> None:
    """Wait for new recording intervals and a playable event playlist."""
    until = time.monotonic() + 150
    cameras_left = set(cameras)
    clip_ready = False
    while time.monotonic() < until:
        for camera in list(cameras_left):
            path = f"/api/{quote(camera, safe='')}/recordings?after={started}"
            if json.loads(fetch(base, path)[0]):
                cameras_left.remove(camera)
        if not clip_ready:
            events = json.loads(
                fetch(base, "/api/events?limit=30&has_clip=1&include_thumbnails=0")[0]
            )
            for event in events:
                if event["start_time"] < started or not event.get("end_time"):
                    continue
                camera = quote(event["camera"], safe="")
                first, last = event["start_time"], event["end_time"]
                clip_path = f"/vod/{camera}/start/{first}/end/{last}/index.m3u8"
                try:
                    playlist = fetch(base, clip_path)[0]
                    if b"#EXTINF:" not in playlist:
                        continue
                    first_segment = next(
                        (
                            line
                            for line in playlist.decode().splitlines()
                            if line and not line.startswith("#")
                        ),
                        None,
                    )
                    if not first_segment:
                        continue
                    segment = urlsplit(urljoin(base + clip_path, first_segment))
                    if segment.netloc != urlsplit(base).netloc:
                        raise RuntimeError(
                            f"Unexpected event media host: {segment.netloc}"
                        )
                    path = segment.path + ("?" + segment.query if segment.query else "")
                    if fetch(base, path)[0]:
                        clip_ready = True
                        break
                except HTTPError as exc:
                    if exc.code not in (400, 404, 502):
                        raise
        if not cameras_left and clip_ready:
            return
        time.sleep(3)
    raise RuntimeError(
        f"Missing recordings: {sorted(cameras_left)}. Playable event: {clip_ready}"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8974")
    parser.add_argument("--started", type=float, required=True)
    args = parser.parse_args()
    base = args.base_url.rstrip("/")
    config = json.loads(fetch(base, "/api/config")[0])
    cameras = [name for name, camera in config["cameras"].items() if camera["enabled"]]
    if len(cameras) != 6:
        raise ValueError(f"Expected six demo inputs. Found {len(cameras)}.")
    check_api(base, 3)
    check_recordings(base, cameras, args.started)
    print("Verified fresh frames, six recordings and a playable event")


if __name__ == "__main__":
    main()
