# /// script
# requires-python = ">=3.11"
# dependencies = ["pillow==13.0.0", "resvg-py==0.5.0"]
# ///
"""Regenerate HeisenCam icons from the original lens SVG with uv run."""
from io import BytesIO
from pathlib import Path

from PIL import Image
from resvg_py import svg_to_bytes

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
DESIGN = WEB / "images/branding"
PUBLIC = WEB / "public/images"
DOCS = ROOT / "docs/static/img/branding"
SOURCE = DESIGN / "favicon.svg"


def lens(size: int) -> Image.Image:
    return Image.open(BytesIO(svg_to_bytes(svg_path=str(SOURCE), width=size, height=size))).convert("RGBA")


def main() -> None:
    for name, size in (("favicon-16x16.png", 16), ("favicon-32x32.png", 32),
                       ("apple-touch-icon.png", 180), ("mstile-150x150.png", 150), ("favicon.png", 512)):
        lens(size).save(DESIGN / name)
    for name, size in (("android-chrome-192x192.png", 192), ("android-chrome-512x512.png", 512),
                       ("apple-touch-icon.png", 180), ("maskable-icon.png", 180), ("maskable-badge.png", 96)):
        icon = lens(size)
        if name == "maskable-icon.png":
            canvas = Image.new("RGBA", (size, size), "#242932")
            inset = size // 8
            canvas.alpha_composite(lens(size - 2 * inset), (inset, inset))
            icon = canvas
        icon.save(PUBLIC / name)
    lens(64).save(DESIGN / "favicon.ico", sizes=[(16, 16), (32, 32), (48, 48), (64, 64)])
    (DOCS / "favicon.ico").write_bytes((DESIGN / "favicon.ico").read_bytes())
    for name in ("logo.svg", "logo-dark.svg"):
        (DOCS / name).write_bytes(SOURCE.read_bytes())
    (ROOT / "site/assets/mark.svg").write_bytes(SOURCE.read_bytes())
    lens(256).save(DOCS / "heisencam.png")
    lens(180).save(ROOT / "frigate/images/birdseye.png")
    offline = Image.new("RGB", (1920, 1080), "#191d24")
    mark = lens(180)
    offline.paste(mark, ((offline.width - 180) // 2, (offline.height - 180) // 2), mark)
    offline.save(ROOT / "frigate/images/camera-error.jpg", quality=86)


if __name__ == "__main__":
    main()
