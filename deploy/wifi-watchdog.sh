#!/usr/bin/env bash
# Recovers wlan0 automatically if it drops off the network, without needing
# a physical power cycle.
#
# Root cause this addresses (see NOTES.md "PiDock network resilience"):
# NetworkManager occasionally hits a "no secrets: No agents were available
# for this request" dead-end while reauthenticating wlan0 — even though the
# WiFi password IS stored in the connection file (psk-flags: 0), because
# this is a headless box with no secrets agent running to service such a
# request if NetworkManager ever asks for one anyway. Once that happens,
# NetworkManager stops auto-retrying that connection entirely and the Pi
# goes fully dark until something kicks it — previously only a power cycle.
#
# Run periodically by wifi-watchdog.timer. Safe to run by hand for a
# manual check: sudo bash deploy/wifi-watchdog.sh
set -euo pipefail

IFACE="wlan0"

get_state() {
    local raw
    raw="$(nmcli -t -f GENERAL.STATE device show "$IFACE" 2>/dev/null || true)"
    raw="${raw#GENERAL.STATE:}"
    echo "${raw%% *}"
}

# Looked up by connection type rather than hardcoding the SSID/connection
# name — this box has exactly one WiFi profile, and it works whether or
# not that profile is currently active (unlike filtering `connection show`
# by DEVICE, which only shows a bound device for already-active profiles).
get_wifi_conn_name() {
    nmcli -t -f NAME,TYPE connection show 2>/dev/null | awk -F: '$2=="802-11-wireless" {print $1; exit}'
}

state="$(get_state)"

if [ "$state" = "100" ]; then
    exit 0  # connected, nothing to do
fi

logger -t wifi-watchdog "wlan0 state is '$state' (not connected) - attempting recovery"

conn_name="$(get_wifi_conn_name)"

# Cheaper and faster than restarting the whole NetworkManager daemon - try
# this first.
if [ -n "$conn_name" ] && nmcli connection up "$conn_name" >/dev/null 2>&1; then
    logger -t wifi-watchdog "recovered via 'nmcli connection up'"
    exit 0
fi

logger -t wifi-watchdog "'nmcli connection up' failed - restarting NetworkManager"
systemctl restart NetworkManager
sleep 15

state="$(get_state)"
if [ "$state" = "100" ]; then
    logger -t wifi-watchdog "recovered via NetworkManager restart"
else
    logger -t wifi-watchdog "still not connected (state '$state') after NetworkManager restart"
fi
