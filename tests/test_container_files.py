import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def test_runtime_image_uses_non_root_user_and_explicit_sources():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")

    assert "USER app" in dockerfile
    assert "COPY . ." not in dockerfile
    assert "COPY --chown=app:app app ./app" in dockerfile
    assert "COPY --chown=app:app migrations ./migrations" in dockerfile
    assert "COPY --chown=app:app wsgi.py ." in dockerfile


def test_docker_build_context_excludes_local_and_sensitive_files():
    ignored = set(
        (ROOT / ".dockerignore").read_text(encoding="utf-8").splitlines()
    )

    assert {
        ".env",
        ".env.*",
        ".git",
        ".test-venv",
        ".venv",
        ".pytest_cache",
        "tests",
    }.issubset(ignored)


def test_compose_publishes_development_ports_only_on_loopback():
    compose = (ROOT / "docker-compose.yml").read_text(encoding="utf-8")
    published_ports = re.findall(
        r'^\s*-\s*"((?:127\.0\.0\.1:)?\d+:\d+)"\s*$',
        compose,
        flags=re.MULTILINE,
    )

    assert published_ports
    assert all(binding.startswith("127.0.0.1:") for binding in published_ports)
