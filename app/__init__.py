from flask import Flask, jsonify
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from .config import Config, validate_runtime_config
from .extensions import db, migrate
from .routes import payments


def create_app(config: type[Config] = Config) -> Flask:
    app = Flask(__name__)
    app.config.from_object(config)
    validate_runtime_config(app.config)

    db.init_app(app)
    migrate.init_app(app, db)
    app.register_blueprint(payments)

    @app.get("/health")
    def health():
        try:
            db.session.execute(text("SELECT 1"))
        except SQLAlchemyError:
            db.session.rollback()
            app.logger.warning(
                "Payment database health check failed.",
                exc_info=True,
            )
            return jsonify(status="unhealthy"), 503

        return jsonify(status="healthy")

    return app
