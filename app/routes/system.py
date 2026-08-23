from flask import Blueprint, current_app, jsonify

from app.services import system_service

bp = Blueprint("system", __name__, url_prefix="/api/system")


@bp.route("/health")
def health():
    return jsonify(system_service.get_system_health(current_app.config["SYSTEM_DISK_PATH"]))
