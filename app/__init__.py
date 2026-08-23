from flask import Flask, jsonify

from app.config import Config
from app.routes import register_routes


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    register_routes(app)

    @app.route("/api/health")
    def api_health():
        return jsonify({"status": "ok"})

    return app
