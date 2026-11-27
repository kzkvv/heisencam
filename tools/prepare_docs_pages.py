"""Add the existing browser demo and legacy redirects to the Docusaurus build."""

import argparse
import json
import shutil
from html import escape
from pathlib import Path
from urllib.parse import urlsplit

OLD_DEMO = "/heisencam/demo/"
OLD_ORIGIN = "https://kzkvv.github.io"
DEFAULT_DOCS_URL = "https://docs.heisen.cam/"
TEXT_ASSETS = {".html", ".js", ".css", ".webmanifest"}


def redirect(destination: str) -> str:
    """Keep query parameters and anchors on old documentation links."""
    href = escape(destination, quote=True)
    return (
        '<!doctype html>\n<html lang="en">\n'
        '<meta charset="utf-8">\n'
        '<title>HeisenCam documentation</title>\n'
        f'<link rel="canonical" href="{href}">\n'
        f'<noscript><meta http-equiv="refresh" content="0;url={href}"></noscript>\n'
        f"<script>location.replace({json.dumps(destination)}"
        " + location.search + location.hash)</script>\n"
        f'<a href="{href}">Continue to the documentation</a>\n'
    )


def prepare(build: Path, published_demo: Path, docs_url: str) -> None:
    """Add public demo assets and redirects without copying the old landing page."""
    if not (build / "guides/heisencam-demo/index.html").is_file():
        raise SystemExit("Build the HeisenCam documentation first.")

    docs_url = docs_url.rstrip("/") + "/"
    demo_url = docs_url + "demo/"
    demo_path = urlsplit(demo_url).path
    pages = list(build.rglob("*.html"))

    demo = build / "demo"
    shutil.copytree(published_demo / "demo", demo)
    shutil.copyfile(published_demo / "style.css", demo / "sources/style.css")
    for filename in ("LICENSE.txt", "UPSTREAM-TRADEMARK.txt"):
        shutil.copyfile(published_demo / filename, build / filename)
    for path in demo.rglob("*"):
        if not path.is_file() or path.suffix not in TEXT_ASSETS:
            continue
        original = path.read_text(encoding="utf-8")
        updated = original.replace(OLD_ORIGIN + OLD_DEMO, demo_url)
        updated = updated.replace(OLD_DEMO, demo_path)
        if path == demo / "sources/index.html":
            updated = updated.replace('href="../../style.css"', 'href="style.css"')
        if updated != original:
            path.write_text(updated, encoding="utf-8")

    for page in pages:
        relative = page.relative_to(build)
        if relative == Path("404.html"):
            continue
        route = relative.as_posix().removesuffix("index.html")
        legacy_page = build / "docs" / relative
        legacy_page.parent.mkdir(parents=True, exist_ok=True)
        legacy_page.write_text(redirect(docs_url + route), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("published_demo", type=Path)
    parser.add_argument("--docs-url", default=DEFAULT_DOCS_URL)
    args = parser.parse_args()
    prepare(args.build, args.published_demo, args.docs_url or DEFAULT_DOCS_URL)
