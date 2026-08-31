import signal
import sys

from app import create_app

app = create_app()


def _release_pihole_session(signum, frame):
    """
    systemctl restart/stop sends SIGTERM, whose default handling skips
    atexit — so without this, every restart abandons the current Pi-hole
    API session instead of closing it. Each abandoned session still
    occupies a seat under Pi-hole's webserver.api.max_sessions cap until
    it naturally expires (up to 30 min), and enough restarts close
    together exhaust that cap, rejecting new logins with
    "api_seats_exceeded" until old sessions time out.
    """
    client = getattr(app, "_pihole_client", None)
    if client is not None:
        client.close()
    sys.exit(0)


signal.signal(signal.SIGTERM, _release_pihole_session)
signal.signal(signal.SIGINT, _release_pihole_session)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
