import os

from flask import Flask, jsonify

from .config import Config
from .extensions import db, migrate, jwt, cors, limiter


def create_app(config_object=Config):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(config_object)

    os.makedirs(app.instance_path, exist_ok=True)

    db.init_app(app)
    migrate.init_app(app, db)
    jwt.init_app(app)
    cors.init_app(app, resources={r"/api/*": {"origins": app.config["CORS_ORIGINS"]}}, supports_credentials=True)
    limiter.init_app(app)

    from . import models  # noqa: F401 -- register models with SQLAlchemy metadata
    from .auth.routes import bp as auth_bp
    from .donations.routes import bp as donations_bp, admin_bp as admin_donations_bp
    from .blog.routes import bp as blog_bp
    from .gallery.routes import bp as gallery_bp
    from .crafts.routes import bp as crafts_bp
    from .team.routes import bp as team_bp
    from .elderly.routes import bp as elderly_bp
    from .attendance.routes import bp as attendance_bp
    from .health.routes import bp as health_bp
    from .medication.routes import bp as medication_bp
    from .volunteers.routes import bp as volunteers_bp
    from .homevisits.routes import bp as homevisits_bp
    from .feeding.routes import bp as feeding_bp
    from .inventory.routes import bp as inventory_bp
    from .activities.routes import bp as activities_bp
    from .assistance.routes import bp as assistance_bp
    from .incidents.routes import bp as incidents_bp
    from .reports.routes import bp as reports_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(donations_bp)
    app.register_blueprint(admin_donations_bp)
    app.register_blueprint(blog_bp)
    app.register_blueprint(gallery_bp)
    app.register_blueprint(crafts_bp)
    app.register_blueprint(team_bp)
    app.register_blueprint(elderly_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(health_bp)
    app.register_blueprint(medication_bp)
    app.register_blueprint(volunteers_bp)
    app.register_blueprint(homevisits_bp)
    app.register_blueprint(feeding_bp)
    app.register_blueprint(inventory_bp)
    app.register_blueprint(activities_bp)
    app.register_blueprint(assistance_bp)
    app.register_blueprint(incidents_bp)
    app.register_blueprint(reports_bp)

    from .cli import seed_admin
    app.cli.add_command(seed_admin)

    @app.get("/api/health")
    def health():
        return jsonify(status="ok"), 200

    @jwt.unauthorized_loader
    def _missing_token(reason):
        return jsonify(error="Authentication required"), 401

    @jwt.invalid_token_loader
    def _invalid_token(reason):
        return jsonify(error="Invalid or expired token"), 401

    @jwt.expired_token_loader
    def _expired_token(jwt_header, jwt_payload):
        return jsonify(error="Token has expired"), 401

    @app.errorhandler(404)
    def _not_found(err):
        return jsonify(error=getattr(err, "description", "Not found")), 404

    @app.errorhandler(400)
    def _bad_request(err):
        return jsonify(error=getattr(err, "description", "Bad request")), 400

    @app.errorhandler(403)
    def _forbidden(err):
        return jsonify(error=getattr(err, "description", "Forbidden")), 403

    return app
