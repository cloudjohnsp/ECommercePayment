import os


class Config:
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "postgresql+psycopg://postgres:postgres@localhost:5433/ecommerce_payment",
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "development-secret")
    WEBHOOK_TIMEOUT_SECONDS = float(os.getenv("WEBHOOK_TIMEOUT_SECONDS", "5"))
