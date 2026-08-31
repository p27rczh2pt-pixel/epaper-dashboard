import requests
from flask import Blueprint, jsonify

from app.services import pihole_service
from app.services.pihole_client import PiholeAPIError, PiholeAuthError

bp = Blueprint("pihole", __name__, url_prefix="/api/pihole")


@bp.route("/stats")
def stats():
    try:
        data = pihole_service.get_dns_stats()
        data["new_devices"] = pihole_service.get_new_devices()
        return jsonify(data)
    except PiholeAuthError as exc:
        return jsonify({"error": "pihole_auth_failed", "message": str(exc)}), 502
    except (PiholeAPIError, requests.RequestException) as exc:
        return jsonify({"error": "pihole_unreachable", "message": str(exc)}), 502


@bp.route("/health")
def health():
    """Pi-hole's own system health (memory/load/uptime), not the Pi Zero's."""
    try:
        return jsonify(pihole_service.get_pihole_system_health())
    except PiholeAuthError as exc:
        return jsonify({"error": "pihole_auth_failed", "message": str(exc)}), 502
    except (PiholeAPIError, requests.RequestException) as exc:
        return jsonify({"error": "pihole_unreachable", "message": str(exc)}), 502


@bp.route("/devices")
def devices():
    try:
        return jsonify(pihole_service.get_device_list())
    except PiholeAuthError as exc:
        return jsonify({"error": "pihole_auth_failed", "message": str(exc)}), 502
    except (PiholeAPIError, requests.RequestException) as exc:
        return jsonify({"error": "pihole_unreachable", "message": str(exc)}), 502
