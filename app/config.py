import math
import os
from collections.abc import MutableMapping

from sqlalchemy import URL


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL")
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    DATABASE_HOST = os.getenv("DATABASE_HOST", "localhost")
    DATABASE_PORT = os.getenv("DATABASE_PORT", "5433")
    DATABASE_NAME = os.getenv("DATABASE_NAME", "ecommerce_payment")
    DATABASE_USER = os.getenv("DATABASE_USER", "postgres")
    DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD") or os.getenv(
        "POSTGRES_PASSWORD"
    )
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET")
    WEBHOOK_TIMEOUT_SECONDS = os.getenv("WEBHOOK_TIMEOUT_SECONDS", "5")


def validate_runtime_config(config: MutableMapping[str, object]) -> None:
    database_uri = config.get("SQLALCHEMY_DATABASE_URI")
    if not (isinstance(database_uri, str) and database_uri.strip()):
        database_password = config.get("DATABASE_PASSWORD")
        if not isinstance(database_password, str) or not database_password:
            raise RuntimeError(
                "DATABASE_URL or DATABASE_PASSWORD is required."
            )

        try:
            database_port = int(str(config.get("DATABASE_PORT", "")))
        except ValueError as exception:
            raise RuntimeError("DATABASE_PORT must be a valid port.") from exception

        if database_port < 1 or database_port > 65535:
            raise RuntimeError("DATABASE_PORT must be a valid port.")

        config["SQLALCHEMY_DATABASE_URI"] = URL.create(
            drivername="postgresql+psycopg",
            username=str(config.get("DATABASE_USER", "postgres")),
            password=database_password,
            host=str(config.get("DATABASE_HOST", "localhost")),
            port=database_port,
            database=str(config.get("DATABASE_NAME", "ecommerce_payment")),
        )

    webhook_secret = config.get("WEBHOOK_SECRET")
    if not isinstance(webhook_secret, str) or not webhook_secret.strip():
        raise RuntimeError("WEBHOOK_SECRET is required.")

    try:
        timeout = float(config.get("WEBHOOK_TIMEOUT_SECONDS", ""))
    except (TypeError, ValueError) as exception:
        raise RuntimeError(
            "WEBHOOK_TIMEOUT_SECONDS must be a positive finite number."
        ) from exception

    if not math.isfinite(timeout) or timeout <= 0:
        raise RuntimeError(
            "WEBHOOK_TIMEOUT_SECONDS must be a positive finite number."
        )

    config["WEBHOOK_TIMEOUT_SECONDS"] = timeout
