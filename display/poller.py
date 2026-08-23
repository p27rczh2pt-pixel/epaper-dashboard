"""
Polls the Flask API's per-source routes, renders the layout, and either:
  - pushes it to the physical e-paper display, or
  - saves it as a PNG preview (--preview), with no e-paper/SPI dependency
    needed for that path.

Run from the Pi Zero (or anywhere, for --preview) with:
    python display/poller.py --preview
    python display/poller.py            # full e-paper refresh
"""

import argparse
import os
import sys

import requests
from dotenv import load_dotenv

sys.path.insert(0, os.path.dirname(__file__))
from render import render_dashboard  # noqa: E402

load_dotenv()

API_BASE = os.environ.get("DASHBOARD_API_BASE", "http://127.0.0.1:5000")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")


def fetch_all():
    endpoints = {
        "pihole_stats": "/api/pihole/stats",
        "pihole_health": "/api/pihole/health",
        "network_health": "/api/network/health",
        "system_health": "/api/system/health",
    }
    data = {}
    for key, path in endpoints.items():
        try:
            resp = requests.get(f"{API_BASE}{path}", timeout=10)
            data[key] = resp.json()
        except requests.RequestException as exc:
            data[key] = {"error": str(exc)}
    return data


def push_to_display(image):
    """
    Full refresh only (epd.init(), not init_fast/init_part) — this display
    doesn't support partial refresh well and ghosting builds up over
    partial updates, so every push is a full redraw.
    """
    try:
        from waveshare_lib import epd7in5_V2
    except ImportError as exc:
        raise RuntimeError(
            "Waveshare driver deps not installed. On the Pi Zero, run: "
            "pip install -r requirements-display.txt"
        ) from exc

    epd = epd7in5_V2.EPD()
    epd.init()
    epd.Clear()
    epd.display(epd.getbuffer(image))
    epd.sleep()


def save_preview(image):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    path = os.path.join(OUTPUT_DIR, "preview.png")
    image.save(path)
    return path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--preview", action="store_true", help="Save PNG instead of pushing to e-paper")
    args = parser.parse_args()

    data = fetch_all()
    image = render_dashboard(data)

    if args.preview:
        path = save_preview(image)
        print(f"Saved preview to {path}")
    else:
        push_to_display(image)


if __name__ == "__main__":
    main()
