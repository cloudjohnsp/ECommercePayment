import pytest

from app import create_app


class ValidConfig:
    SQLALCHEMY_DATABASE_URI = "sqlite+pysqlite:///:memory:"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WEBHOOK_SECRET = "test-webhook-secret-with-at-least-32-bytes"
    WEBHOOK_TIMEOUT_SECONDS = "5"


@pytest.mark.parametrize(
    ("setting", "value", "message"),
    [
        (
            "SQLALCHEMY_DATABASE_URI",
            None,
            "DATABASE_URL or DATABASE_PASSWORD is required",
        ),
        ("WEBHOOK_SECRET", "   ", "WEBHOOK_SECRET is required"),
        (
            "WEBHOOK_SECRET",
            "short-secret",
            "WEBHOOK_SECRET must contain at least 32 UTF-8 bytes",
        ),
        (
            "WEBHOOK_TIMEOUT_SECONDS",
            "invalid",
            "WEBHOOK_TIMEOUT_SECONDS must be a positive finite number",
        ),
        (
            "WEBHOOK_TIMEOUT_SECONDS",
            "0",
            "WEBHOOK_TIMEOUT_SECONDS must be a positive finite number",
        ),
        (
            "WEBHOOK_TIMEOUT_SECONDS",
            "NaN",
            "WEBHOOK_TIMEOUT_SECONDS must be a positive finite number",
        ),
    ],
)
def test_create_app_rejects_invalid_runtime_configuration(setting, value, message):
    invalid_config = type(
        "InvalidConfig",
        (ValidConfig,),
        {setting: value},
    )

    with pytest.raises(RuntimeError, match=message):
        create_app(invalid_config)


def test_create_app_normalizes_webhook_timeout_to_float():
    app = create_app(ValidConfig)

    assert app.config["WEBHOOK_TIMEOUT_SECONDS"] == 5.0


def test_create_app_accepts_multibyte_webhook_secret_with_32_utf8_bytes():
    multibyte_config = type(
        "MultibyteConfig",
        (ValidConfig,),
        {"WEBHOOK_SECRET": "á" * 16},
    )

    app = create_app(multibyte_config)

    assert len(app.config["WEBHOOK_SECRET"].encode("utf-8")) == 32


def test_create_app_builds_database_url_without_reparsing_special_password():
    database_config = type(
        "DatabaseConfig",
        (ValidConfig,),
        {
            "SQLALCHEMY_DATABASE_URI": None,
            "DATABASE_HOST": "postgres",
            "DATABASE_PORT": "5432",
            "DATABASE_NAME": "ecommerce_payment",
            "DATABASE_USER": "postgres",
            "DATABASE_PASSWORD": "p@ss:/word",
        },
    )

    app = create_app(database_config)

    assert app.config["SQLALCHEMY_DATABASE_URI"].password == "p@ss:/word"
