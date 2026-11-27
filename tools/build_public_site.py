"""Assemble the HeisenCam landing page, browser demo and Docusaurus build."""

import argparse
import hashlib
import json
import re
import shutil
import subprocess
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SITE = ROOT / "site"
MEDIA = ROOT / "examples" / "demo" / "media"


def write_camera_credits(demo: Path, catalog: dict, demo_url: str) -> None:
    """Write publisher attribution next to the static demo application."""
    sections = []
    for key, source in catalog["publishers"].items():
        cameras = [
            f'<li><a href="../#{escape(cam["id"])}">{escape(cam["name"])}</a> ({escape(cam["sourceName"])})'
            f' · <a href="{escape(cam["sourceUrl"])}">Publisher feed</a></li>'
            for cam in catalog["cameras"]
            if cam["publisher"] == key
        ]
        sections.append(
            f"<h2>{escape(source['name'])}</h2><p>{escape(source['credit'])}</p>"
            f'<p><a href="{escape(source["catalog"])}">Camera catalog</a>'
            f' · <a href="{escape(source["terms"])}">Terms of use</a></p>'
            + "<ul>"
            + "".join(cameras)
            + "</ul>"
        )
    sources = demo / "sources"
    sources.mkdir()
    shutil.copyfile(SITE / "style.css", sources / "style.css")
    (sources / "index.html").write_text(
        '<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        "<title>Camera sources | HeisenCam</title>"
        f'<link rel="canonical" href="{escape(demo_url)}sources/">'
        '<link rel="stylesheet" href="style.css">'
        '<main class="shell"><p><a href="../">Back to HeisenCam</a></p>'
        "<h1>Demo recording sources</h1>"
        f"<p>Samples captured on {escape(catalog['captureDate'])}. "
        '<a href="../catalog.json">Camera catalog and sample digests</a>.</p>'
        + "".join(sections)
        + "</main></html>\n",
        encoding="utf-8",
    )


def package_demo(demo: Path, demo_url: str, revision: str) -> None:
    """Package the current web build and the published sample media."""
    app = ROOT / "web" / "dist-demo"
    if not (app / "index.html").is_file():
        raise SystemExit("Run npm run build:demo in web/ before packaging the site.")
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
        with (MEDIA / f"{name}.mp4").open("rb") as movie:
            if hashlib.file_digest(movie, "sha256").hexdigest() != camera["sha256"]:
                raise ValueError(f"Incorrect media digest for {name}")
    if len(durations) != 6 or not catalog["events"]:
        raise ValueError("The demo requires six cameras and a selection of detections.")
    for event in catalog["events"]:
        if not re.fullmatch(r"[a-z0-9_-]+", event["id"]):
            raise ValueError(f"Invalid demo event ID: {event['id']}")
        if not 0 <= event["offset"] < durations[event["camera"]]:
            raise ValueError(f"Event is outside its sample: {event['id']}")
        if not (SITE / f"demo/events/{event['id']}.webp").is_file():
            raise ValueError(f"Missing snapshot for {event['id']}")
    shutil.copytree(SITE / "demo", demo)
    shutil.copytree(app, demo, dirs_exist_ok=True)
    movies = demo / "media"
    movies.mkdir()
    for name in durations:
        shutil.copy2(MEDIA / f"{name}.mp4", movies)
        preview = demo / "api" / name
        preview.mkdir(parents=True)
        shutil.copyfile(demo / "posters" / f"{name}.webp", preview / "latest.webp")
    for event in catalog["events"]:
        event_id = event["id"]
        thumbnail = demo / "api" / "events" / event_id
        thumbnail.mkdir(parents=True)
        shutil.copyfile(
            demo / "events" / f"{event_id}.webp", thumbnail / "thumbnail.webp"
        )

    # Pages serves real directories for React Router deep links.
    html = (demo / "index.html").read_text(encoding="utf-8")
    base = urlsplit(demo_url).path
    poster = escape(demo_url + "posters/fortieth_street.webp", quote=True)
    for route in ("", "events/", "birdseye/"):
        (demo / route).mkdir(exist_ok=True)
        location = escape(demo_url + route, quote=True)
        metadata = (
            f'<link rel="canonical" href="{location}">'
            '<meta property="og:title" content="HeisenCam demo">'
            '<meta property="og:description" content="Explore six cameras and play sample events.">'
            f'<meta property="og:url" content="{location}">'
            f'<meta property="og:image" content="{poster}">'
            f'<meta name="heisencam-source-revision" content="{escape(revision, quote=True)}">'
        )
        (demo / route / "index.html").write_text(
            html.replace("</head>", metadata + "</head>"), encoding="utf-8"
        )
    for manifest in demo.rglob("*.webmanifest"):
        manifest.write_text(manifest.read_text().replace("/BASE_PATH/", base))
    write_camera_credits(demo, catalog, demo_url)
    print(f"Packaged {len(durations)} cameras and {len(catalog['events'])} events")


def source_revision() -> str:
    """Identify the checkout used to produce the demo and docs."""
    return subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()


def build(output: Path) -> None:
    """Assemble a local preview of the landing page and demo."""
    docs = ROOT / "docs" / "build"
    if not (docs / "guides/heisencam-demo/index.html").is_file():
        raise SystemExit("Build the documentation in docs/ before packaging the site.")
    for source in (SITE, MEDIA, docs, ROOT / "web" / "dist-demo"):
        if output == source or source in output.parents:
            raise SystemExit("Choose an output directory outside the site inputs.")
    if output.exists() and any(output.iterdir()):
        raise SystemExit("Choose an empty output directory for this build.")
    shutil.copytree(
        SITE, output, ignore=shutil.ignore_patterns("demo"), dirs_exist_ok=True
    )
    shutil.copytree(docs, output / "docs")
    shutil.copyfile(ROOT / "LICENSE", output / "LICENSE.txt")
    shutil.copyfile(ROOT / "TRADEMARK.md", output / "UPSTREAM-TRADEMARK.txt")
    package_demo(
        output / "demo", "https://kzkvv.github.io/heisencam/demo/", source_revision()
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path, help="An empty or new output directory")
    build(parser.parse_args().output.resolve())
