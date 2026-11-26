"""Assemble the HeisenCam landing page, browser demo and Docusaurus build."""

import argparse
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
MEDIA = ROOT / "examples" / "demo" / "media"


def build(output: Path) -> None:
    """Package only the published sample files and the compiled documentation."""
    docs = ROOT / "docs" / "build"
    if not (docs / "guides/heisencam-demo/index.html").is_file():
        raise SystemExit("Build the documentation in docs/ before packaging the site.")
    catalog = json.loads((SITE / "demo/catalog.json").read_text())
    durations = {}
    for camera in catalog["cameras"]:
        name = camera["id"]
        if not re.fullmatch(r"[a-z][a-z0-9_]*", name) or name in durations:
            raise ValueError(f"Invalid or duplicate camera ID: {name}")
        durations[name] = camera["seconds"]
        for asset in (MEDIA / f"{name}.mp4", SITE / f"demo/posters/{name}.webp"):
            if not asset.is_file():
                raise FileNotFoundError(asset)
    if len(durations) != 6 or not catalog["events"]:
        raise ValueError("The demo requires six cameras and a selection of detections.")
    for event in catalog["events"]:
        if not 0 <= event["offset"] < durations[event["camera"]]:
            raise ValueError(f"Event is outside its sample: {event['id']}")
        if not (SITE / f"demo/events/{event['id']}.webp").is_file():
            raise ValueError(f"Missing snapshot for {event['id']}")
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Choose an empty output directory for this build.")
    shutil.copytree(SITE, output, dirs_exist_ok=True)
    shutil.copytree(docs, output / "docs")
    movies = output / "demo" / "media"
    movies.mkdir()
    for name in durations:
        shutil.copy2(MEDIA / f"{name}.mp4", movies)
    print(
        f"Packaged {len(durations)} cameras, {len(catalog['events'])} events and docs in {output}"
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="An empty or new output directory")
    build(parser.parse_args().output.resolve())
