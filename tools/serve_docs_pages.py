"""Serve a packaged Pages build locally under an optional URL prefix."""

import argparse
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main() -> None:
    """Mount the generated files at the same URL prefix used in production."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--prefix", default="")
    args = parser.parse_args()
    prefix = args.prefix.rstrip("/")
    build = Path(__file__).resolve().parents[1] / "docs/build"

    class PagesHandler(SimpleHTTPRequestHandler):
        def send_head(self):
            if prefix and not self.path.startswith(prefix + "/"):
                self.send_error(404)
                return None
            return super().send_head()

        def translate_path(self, path: str) -> str:
            return super().translate_path(path[len(prefix) :])

    handler = partial(PagesHandler, directory=build)
    ThreadingHTTPServer(("127.0.0.1", args.port), handler).serve_forever()


if __name__ == "__main__":
    main()
