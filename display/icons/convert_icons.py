"""
One-off utility to (re)generate this directory's icon PNGs from their
source SVGs. Not used at runtime by render.py — run manually if an icon
needs to be swapped or re-rendered at a different size.

Source SVGs aren't vendored here (only the converted PNGs are); re-fetch
them from the URLs below if you need to regenerate:

  pihole.svg      https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/pihole.svg
  raspberrypi.svg https://raw.githubusercontent.com/simple-icons/simple-icons/develop/icons/raspberrypi.svg
  globe.svg       https://raw.githubusercontent.com/feathericons/feather/main/icons/globe.svg
  cpu.svg         https://raw.githubusercontent.com/feathericons/feather/main/icons/cpu.svg

Requires PyGObject + GdkPixbuf/librsvg for SVG rasterization (apt package
on Debian/Raspberry Pi OS: `python3-gi`, `librsvg2-common`) — not a pip
dependency of this project, since it's only needed for this one-off step.

Usage: python3 convert_icons.py /path/to/icon_sources_dir
(expects pihole.svg, raspberrypi.svg, globe.svg, cpu.svg in that dir)
"""

import os
import re
import sys

import gi

gi.require_version("GdkPixbuf", "2.0")
from gi.repository import GdkPixbuf  # noqa: E402
from PIL import Image  # noqa: E402

SIZE = 40

# (source filename, output filename, needs stroke="currentColor" pinned to black)
JOBS = [
    ("pihole.svg", "pihole.png", False),
    ("raspberrypi.svg", "raspberrypi.png", False),
    ("globe.svg", "globe.png", True),
    ("cpu.svg", "cpu.png", True),
]


def convert(src_dir, out_dir):
    for src_name, out_name, needs_color_fix in JOBS:
        src_path = os.path.join(src_dir, src_name)
        with open(src_path) as f:
            svg = f.read()

        if needs_color_fix:
            # Feather icons use stroke="currentColor"; pin it explicitly to
            # black rather than relying on the renderer's default.
            svg = re.sub(r"(<svg\b)", r'\1 color="black"', svg, count=1)

        tmp_path = os.path.join(src_dir, f"_fixed_{out_name}.svg")
        with open(tmp_path, "w") as f:
            f.write(svg)

        pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(tmp_path, SIZE, SIZE, True)
        w, h, stride = pixbuf.get_width(), pixbuf.get_height(), pixbuf.get_rowstride()
        img = Image.frombytes("RGBA", (w, h), bytes(pixbuf.get_pixels()), "raw", "RGBA", stride)

        # Flatten to pure black-on-transparent — alpha channel only, RGB zeroed.
        alpha = img.split()[-1]
        flat = Image.merge("RGBA", (Image.new("L", img.size, 0),) * 3 + (alpha,))

        out_path = os.path.join(out_dir, out_name)
        flat.save(out_path)
        os.remove(tmp_path)
        print(f"{out_name}: saved {flat.size}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)
    convert(sys.argv[1], os.path.dirname(os.path.abspath(__file__)))
