"""Production configuration: database URL handling and CORS restrictions."""

import pytest

from app.core.config import normalise_database_url


@pytest.mark.parametrize("given,expected", [
    ("postgres://u:p@host:5432/db", "postgresql+psycopg://u:p@host:5432/db"),        # Render / Heroku style
    ("postgresql://u:p@host/db?sslmode=require", "postgresql+psycopg://u:p@host/db?sslmode=require"),  # Neon
    ("postgresql+psycopg://u:p@host/db", "postgresql+psycopg://u:p@host/db"),         # already explicit
    ("sqlite:///var/sentinel.db", "sqlite:///var/sentinel.db"),
])
def test_database_url_is_normalised_for_psycopg(given, expected):
    assert normalise_database_url(given) == expected


def _preflight(client, origin):
    return client.options("/api/analyze/text", headers={
        "Origin": origin, "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "content-type,x-sentinel-client"})


def test_cors_allows_configured_origin(client):
    r = _preflight(client, "http://localhost:3000")
    assert r.status_code == 200
    assert r.headers["access-control-allow-origin"] == "http://localhost:3000"
    assert "x-sentinel-client" in r.headers["access-control-allow-headers"].lower()


def test_cors_rejects_unknown_origin(client):
    r = _preflight(client, "https://evil.example.com")
    assert r.status_code == 400
    assert "access-control-allow-origin" not in r.headers
    # A simple GET from a disallowed origin gets no CORS header, so browsers block the response.
    r = client.get("/api/health", headers={"Origin": "https://evil.example.com"})
    assert "access-control-allow-origin" not in r.headers


def test_cors_never_uses_wildcard(client):
    r = client.get("/api/health", headers={"Origin": "http://localhost:3000"})
    assert r.headers.get("access-control-allow-origin") != "*"
