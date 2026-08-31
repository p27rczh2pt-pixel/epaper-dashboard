#!/usr/bin/env bash
# Installs/updates the epaper-dashboard systemd units on the Pi Zero and
# (re)starts them. Safe to re-run after editing a unit file.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

sudo cp "$SCRIPT_DIR/systemd/epaper-api.service" /etc/systemd/system/
sudo cp "$SCRIPT_DIR/systemd/wifi-watchdog.service" /etc/systemd/system/
sudo cp "$SCRIPT_DIR/systemd/wifi-watchdog.timer" /etc/systemd/system/
sudo chmod +x "$SCRIPT_DIR/wifi-watchdog.sh"

sudo systemctl daemon-reload
sudo systemctl enable --now epaper-api.service
sudo systemctl enable --now wifi-watchdog.timer

echo
echo "Installed. Useful commands:"
echo "  systemctl status epaper-api.service"
echo "  journalctl -u epaper-api.service -n 50 --no-pager"
echo "  systemctl list-timers wifi-watchdog.timer"
echo "  journalctl -t wifi-watchdog -n 50 --no-pager"
