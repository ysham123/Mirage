from src.httpx_client import create_mirage_client


def test_create_mirage_client_uses_environment_defaults(monkeypatch):
    monkeypatch.setenv("MIRAGE_PROXY_URL", "http://mirage.local")
    monkeypatch.setenv("MIRAGE_RUN_ID", "env-run")

    with create_mirage_client() as client:
        assert str(client.base_url) == "http://mirage.local"
        assert client.headers["X-Mirage-Run-Id"] == "env-run"


def test_create_mirage_client_preserves_explicit_header(monkeypatch):
    monkeypatch.setenv("MIRAGE_RUN_ID", "env-run")

    with create_mirage_client(headers={"X-Mirage-Run-Id": "explicit-run"}) as client:
        assert client.headers["X-Mirage-Run-Id"] == "explicit-run"
