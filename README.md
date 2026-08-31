# epaper-dashboard

Flask API that aggregates home-network stats, plus a browser dashboard
served from the same app for viewing on an iPad (or any device) on the
LAN. Runs on a Raspberry Pi Zero 2 W ("PiDock"). Formerly drove a
Waveshare e-paper panel directly from the Pi; that hardware died and was
removed, so the display now lives entirely in the browser.

## Structure

```
app/                    Flask API + web dashboard
  routes/               One blueprint per data source (thin: parse request, call service, jsonify)
                         plus dashboard.py, which serves the browser page
  services/              One module per data source (fetch + normalize the actual data)
  templates/dashboard.html   The iPad-facing page: rotates through a few full-screen views
  static/icons/          Color icons used on the dashboard page
  config.py              Env-driven config

tests/                  pytest
```

Adding a new data source later = one new file in `services/`, one new
blueprint in `routes/`, register it in `app/routes/__init__.py`.

## Setup

```
cp .env.example .env    # fill in PIHOLE_APP_PASSWORD, etc.
pip install -r requirements.txt
python run.py
```

Pi-hole app password: Pi-hole v6 web UI > Settings > API > "App Password" (generate one there).

Flask listens on `0.0.0.0:5000`, so once running it's reachable from
other devices on the LAN at `http://<pi-host>:5000/` — that's the URL to
open in Safari on the iPad and add to the home screen.

Run tests:

```
pip install -r requirements-dev.txt
pytest
```

## Deploying to the Pi Zero

```
rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='data/' \
  ./ pi-user@pi-host:~/epaper-dashboard/

ssh pi-user@pi-host
cd ~/epaper-dashboard
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
bash deploy/install_systemd.sh              # installs + starts the systemd service (see below)
```

`--exclude='data/'` matters: that's where `known_devices.json` (new-device
tracking, see below) lives on the Pi — never overwrite it from a dev
machine's copy.

Confirmed working end-to-end on a real Pi Zero 2 W (Debian 13/trixie).

## Running automatically (systemd)

`deploy/install_systemd.sh` (safe to re-run after editing a unit) installs:

- `epaper-api.service` — the Flask API (and dashboard page), always running, restarts on failure.
- `wifi-watchdog.timer` + `.service` — runs `deploy/wifi-watchdog.sh` every
  3 minutes; if `wlan0` isn't connected, tries to bring it back up
  automatically (see NOTES.md for the failure mode this recovers from —
  a headless-box NetworkManager quirk that otherwise needs a physical
  power cycle to clear).

```
systemctl status epaper-api.service
journalctl -u epaper-api.service -n 50 --no-pager

systemctl list-timers wifi-watchdog.timer
journalctl -t wifi-watchdog -n 50 --no-pager
```

## Viewing on the iPad

No app, no kiosk browser service on the Pi — the browser lives entirely
on the iPad:

1. Open `http://<pi-host>:5000/` in Safari on the iPad.
2. Share sheet > Add to Home Screen, so it launches full-screen like an app.
3. Optionally turn on Guided Access (Settings > Accessibility) to lock
   the iPad into the dashboard.

The page rotates through Pi-hole / Network / System views automatically
and refreshes its data in the background — no interaction needed once
it's up.

## Status

- [x] Pi-hole DNS stats + Pi-hole system health (`/api/pihole/stats`, `/api/pihole/health`)
- [x] Network health — ping + external IP/ISP (`/api/network/health`)
- [x] Pi Zero system health — CPU temp/uptime/disk (`/api/system/health`)
- [x] Browser dashboard (`/`) — rotates through Pi-hole / Network / System views, styled for iPad landscape
- [x] Query rate anomaly flag — in-memory rolling baseline in `app/services/anomaly_service.py`, flagged in the DNS panel
- [x] New device detection — persisted device inventory diff in `app/services/device_tracker.py`, badge in the Network panel
