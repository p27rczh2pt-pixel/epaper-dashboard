from flask import Blueprint, current_app, jsonify

from app.services import network_service

bp = Blueprint("network", __name__, url_prefix="/api/network")


@bp.route("/health")
def health():
    return jsonify(network_service.get_network_health(current_app.config))
