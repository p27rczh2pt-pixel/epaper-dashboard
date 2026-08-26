# epaper-dashboard

Flask API that aggregates home-network stats, plus a poller/renderer that
draws the dashboard and pushes it to a Waveshare 7.5" e-paper display
(epd7in5_V2, 800x480, full refresh only) via a Raspberry Pi Zero 2 W.

## Structure

```
app/                    Flask API
  routes/               One blueprint per data source (thin: parse request, call service, jsonify)
  services/              One module per data source (fetch + normalize the actual data)
  config.py              Env-driven config

display/                Runs on the Pi Zero, separate from the Flask app
  poller.py              Polls the API routes, renders, pushes to e-paper (or --preview to PNG)
  render.py              PIL layout, no e-paper/SPI dependency
  waveshare_lib/         Vendored Waveshare epd7in5_V2 driver (see its README)
  output/                Preview PNGs land here

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

Run tests:

```
pip install -r requirements-dev.txt
pytest
```

## Preview without touching the e-paper display

```
python display/poller.py --preview
```

Saves `display/output/preview.png` — full e-paper refreshes are slow, so
use this while iterating on layout.

## Deploying to the Pi Zero

```
rsync -avz --exclude='.venv' --exclude='__pycache__' --exclude='display/output/*.png' --exclude='data/' \
  ./ pi-user@pi-host:~/epaper-dashboard/

ssh pi-user@pi-host
cd ~/epaper-dashboard
sudo apt install -y python3-lgpio          # see requirements-display.txt for why
python3 -m venv --system-site-packages .venv   # NOT a plain `venv` — see above
.venv/bin/pip install -r requirements-display.txt
bash deploy/install_systemd.sh              # installs + starts the systemd service/timer (see below)
```

`--exclude='data/'` matters: that's where `known_devices.json` (new-device
tracking, see below) lives on the Pi — never overwrite it from a dev
machine's copy.

Confirmed working end-to-end on a real Pi Zero 2 W (Debian 13/trixie).

## Running automatically (systemd)

`deploy/systemd/` has two units, installed by `deploy/install_systemd.sh`
(safe to re-run after editing one):

- `epaper-api.service` — the Flask API, always running, restarts on failure.
- `epaper-poller.timer` + `epaper-poller.service` — polls + pushes a full
  refresh every 15 minutes (edit `OnUnitActiveSec` in the `.timer` file to
  change the interval, then re-run the install script).

```
systemctl status epaper-api.service
systemctl list-timers epaper-poller.timer
journalctl -u epaper-poller.service -n 50 --no-pager
sudo systemctl start epaper-poller.service   # trigger a push right now
```

## Status

- [x] Pi-hole DNS stats + Pi-hole system health (`/api/pihole/stats`, `/api/pihole/health`)
- [x] Network health — ping + external IP/ISP (`/api/network/health`)
- [x] Pi Zero system health — CPU temp/uptime/disk (`/api/system/health`)
- [x] PIL layout in `display/render.py` (2x2 panel grid, degrades gracefully on per-source errors)
- [x] Waveshare driver vendored into `display/waveshare_lib/` and wired into `display/poller.py`
- [x] Real end-to-end hardware validation on the Pi Zero
- [x] Scheduling via systemd service + timer, running every 15 minutes
- [x] Query rate anomaly flag — in-memory rolling baseline in `app/services/anomaly_service.py`, flagged in the DNS panel
- [x] New device detection — persisted device inventory diff in `app/services/device_tracker.py`, badge in the Network panel
