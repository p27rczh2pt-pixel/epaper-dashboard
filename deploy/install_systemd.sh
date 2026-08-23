#!/usr/bin/env bash
# Installs/updates the epaper-dashboard systemd units on the Pi Zero and
# (re)starts them. Safe to re-run after editing a unit file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sudo cp "$SCRIPT_DIR/systemd/epaper-api.service" /etc/systemd/system/
sudo cp "$SCRIPT_DIR/systemd/epaper-poller.service" /etc/systemd/system/
sudo cp "$SCRIPT_DIR/systemd/epaper-poller.timer" /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable --now epaper-api.service
sudo systemctl enable --now epaper-poller.timer

echo
echo "Installed. Useful commands:"
echo "  systemctl status epaper-api.service"
echo "  systemctl list-timers epaper-poller.timer"
echo "  journalctl -u epaper-poller.service -n 50 --no-pager"
echo "  sudo systemctl start epaper-poller.service   # trigger a push right now"
