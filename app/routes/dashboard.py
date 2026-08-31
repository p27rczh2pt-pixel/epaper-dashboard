from flask import Blueprint, render_template

bp = Blueprint("dashboard", __name__)


@bp.route("/")
def dashboard():
    """
    The iPad-facing dashboard: a static page shell that rotates through a
    few full-screen views. All data comes from client-side JS polling the
    existing /api/* routes.
    """
    return render_template("dashboard.html")
