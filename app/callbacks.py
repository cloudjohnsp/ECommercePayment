from collections.abc import Iterable
from urllib.parse import SplitResult, urlsplit


def normalize_http_origin(value: str) -> str | None:
    if not value or "\\" in value or any(ord(character) < 32 for character in value):
        return None

    try:
        parsed = urlsplit(value)
        port = parsed.port
    except ValueError:
        return None

    scheme = parsed.scheme.lower()
    if (
        scheme not in {"http", "https"}
        or parsed.hostname is None
        or parsed.username is not None
        or parsed.password is not None
    ):
        return None

    try:
        host = parsed.hostname.rstrip(".").encode("idna").decode("ascii").lower()
    except UnicodeError:
        return None
    if not host:
        return None

    default_port = 80 if scheme == "http" else 443
    formatted_host = f"[{host}]" if ":" in host else host
    port_suffix = f":{port}" if port is not None and port != default_port else ""
    return f"{scheme}://{formatted_host}{port_suffix}"


def parse_allowed_callback_origins(value: object) -> frozenset[str]:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("ALLOWED_CALLBACK_ORIGINS is required.")

    origins: set[str] = set()
    for item in _split_origins(value):
        parsed = urlsplit(item)
        normalized = normalize_http_origin(item)
        if (
            normalized is None
            or parsed.path not in {"", "/"}
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError(
                "ALLOWED_CALLBACK_ORIGINS must contain only absolute HTTP or HTTPS origins."
            )
        origins.add(normalized)

    if not origins:
        raise ValueError("ALLOWED_CALLBACK_ORIGINS is required.")
    return frozenset(origins)


def _split_origins(value: str) -> Iterable[str]:
    return (item.strip() for item in value.split(",") if item.strip())
