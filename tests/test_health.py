from unittest.mock import patch

from sqlalchemy.exc import SQLAlchemyError

from app.extensions import db


def test_health_returns_healthy_when_database_is_available(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json == {"status": "healthy"}


def test_health_returns_unhealthy_when_database_is_unavailable(app):
    with app.app_context(), patch.object(
        db.session,
        "execute",
        side_effect=SQLAlchemyError("database unavailable"),
    ):
        response = app.test_client().get("/health")

    assert response.status_code == 503
    assert response.json == {"status": "unhealthy"}
