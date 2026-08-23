from app.routes import network, pihole, system


def register_routes(app):
    app.register_blueprint(pihole.bp)
    app.register_blueprint(network.bp)
    app.register_blueprint(system.bp)
