def test_serve_always_binds_loopback(monkeypatch):
    from doc_tasks import cli
    seen = {}
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **kwargs: seen.update(kwargs))
    cli.main(["serve", "--port", "8132"])
    assert seen["host"] == "127.0.0.1"
    assert seen["port"] == 8132


def test_production_refuses_qwen(monkeypatch):
    import pytest

    from doc_tasks.runtime import Settings
    monkeypatch.setenv("DOC_TASKS_MODEL", "qwen3.5:4b")
    with pytest.raises(ValueError, match="Production requires Tev1"):
        Settings()
