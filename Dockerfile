FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN groupadd --system --gid 10001 app \
    && useradd --system --uid 10001 --gid app --home-dir /app app

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY --chown=app:app app ./app
COPY --chown=app:app migrations ./migrations
COPY --chown=app:app wsgi.py .

USER app

EXPOSE 5000
CMD ["sh", "-c", "flask --app wsgi db upgrade && gunicorn --bind 0.0.0.0:5000 --workers 2 wsgi:app"]
