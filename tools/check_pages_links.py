"""Check internal HTML routes and static assets in the packaged Pages build."""

import argparse
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import unquote, urljoin, urlsplit

REFERENCE_ATTRIBUTES = {
    "a": ("href",),
    "img": ("src",),
    "script": ("src",),
    "link": ("href",),
    "video": ("src", "poster"),
    "source": ("src",),
}


class PageLinks(HTMLParser):
    """Collect document and asset URLs."""

    def __init__(self) -> None:
        super().__init__()
        self.references: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        keys = REFERENCE_ATTRIBUTES.get(tag, ())
        self.references.extend(value for key, value in attrs if key in keys and value)


def check(build: Path, site: str) -> None:
    """Verify that URLs under this site's origin and prefix resolve locally."""
    site = site.rstrip("/") + "/"
    address = urlsplit(site)
    pages = sorted(build.rglob("*.html"))
    if not pages:
        raise SystemExit("No HTML files in the Pages artifact")
    failures: dict[str, str] = {}
    for page in pages:
        route = page.relative_to(build).as_posix().removesuffix("index.html")
        links = PageLinks()
        links.feed(page.read_text(encoding="utf-8"))
        for ref in links.references:
            if ref.startswith("#"):
                continue
            url = urlsplit(urljoin(site + route, ref))
            if (url.scheme, url.netloc) != (address.scheme, address.netloc):
                continue
            if not url.path.startswith(address.path):
                # Repository Pages can share the same hosting origin.
                continue
            target = build / unquote(url.path.removeprefix(address.path))
            if (
                target.is_file()
                or (target / "index.html").is_file()
                or (target.name and target.with_suffix(".html").is_file())
            ):
                continue
            failures.setdefault(url.path, route)
    for path, route in sorted(failures.items()):
        print(f"{route or '/'} → {path}")
    if failures:
        raise SystemExit(f"{len(failures)} broken local links or assets")
    print(f"Checked links and assets in {len(pages)} HTML pages")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("--docs-url", default="https://docs.heisen.cam/")
    args = parser.parse_args()
    check(args.build, args.docs_url or "https://docs.heisen.cam/")
