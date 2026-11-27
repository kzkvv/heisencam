"""Add the compiled browser demo and legacy redirects to the documentation."""

import argparse
import json
import shutil
from html import escape
from pathlib import Path

from build_public_site import ROOT, package_demo, source_revision

DEFAULT_DOCS_URL = "https://docs.heisen.cam/"


def redirect(destination: str) -> str:
    """Keep query parameters and anchors on old documentation links."""
    href = escape(destination, quote=True)
    return (
        '<!doctype html>\n<html lang="en">\n'
        '<meta charset="utf-8">\n'
        "<title>HeisenCam documentation</title>\n"
        f'<link rel="canonical" href="{href}">\n'
        f'<noscript><meta http-equiv="refresh" content="0;url={href}"></noscript>\n'
        f"<script>location.replace({json.dumps(destination)}"
        " + location.search + location.hash)</script>\n"
        f'<a href="{href}">Continue to the documentation</a>\n'
    )


def prepare(build: Path, docs_url: str) -> None:
    """Add public demo assets and redirects without copying the old landing page."""
    if not (build / "guides/heisencam-demo/index.html").is_file():
        raise SystemExit("Build the HeisenCam documentation first.")

    docs_url = docs_url.rstrip("/") + "/"
    demo_url = docs_url + "demo/"
    pages = list(build.rglob("*.html"))
    revision = source_revision()
    package_demo(build / "demo", demo_url, revision)
    (build / "source-revision.json").write_text(
        json.dumps({"revision": revision}) + "\n", encoding="utf-8"
    )
    shutil.copyfile(ROOT / "LICENSE", build / "LICENSE.txt")
    shutil.copyfile(ROOT / "TRADEMARK.md", build / "UPSTREAM-TRADEMARK.txt")

    for page in pages:
        relative = page.relative_to(build)
        if relative == Path("404.html"):
            continue
        route = relative.as_posix().removesuffix("index.html")
        legacy_page = build / "docs" / relative
        legacy_page.parent.mkdir(parents=True, exist_ok=True)
        legacy_page.write_text(redirect(docs_url + route), encoding="utf-8")

    for prefix in ("", "docs/"):
        old_api = build / prefix / "integrations/api/frigate-http-api/index.html"
        old_api.parent.mkdir(parents=True, exist_ok=True)
        old_api.write_text(
            redirect(docs_url + "integrations/api/http-api/"), encoding="utf-8"
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("--docs-url", default=DEFAULT_DOCS_URL)
    args = parser.parse_args()
    prepare(args.build, args.docs_url or DEFAULT_DOCS_URL)
