import importlib
from types import SimpleNamespace

import pytest


def _reload_web_ui_module(monkeypatch, env_value=None):
    """Helper to reload module with controlled environment."""
    from langflix.youtube import web_ui

    # Clear environment variables before reload
    monkeypatch.delenv("LANGFLIX_API_BASE_URL", raising=False)
    monkeypatch.delenv("LANGFLIX_RUNNING_IN_DOCKER", raising=False)

    if env_value is not None:
        for key, value in env_value.items():
            monkeypatch.setenv(key, value)

    return importlib.reload(web_ui)


def test_resolve_api_base_prefers_env(monkeypatch):
    web_ui = _reload_web_ui_module(monkeypatch, {"LANGFLIX_API_BASE_URL": "http://example.com/api/"})
    assert web_ui.resolve_api_base_url() == "http://example.com/api"


def test_resolve_api_base_docker_default(monkeypatch):
    web_ui = _reload_web_ui_module(monkeypatch)
    monkeypatch.setattr(web_ui, "_is_running_inside_docker", lambda: True)
    assert web_ui.resolve_api_base_url() == web_ui.DEFAULT_API_BASE_DOCKER


def test_resolve_api_base_local_default(monkeypatch):
    web_ui = _reload_web_ui_module(monkeypatch)
    monkeypatch.setattr(web_ui, "_is_running_inside_docker", lambda: False)
    assert web_ui.resolve_api_base_url() == web_ui.DEFAULT_API_BASE_LOCAL

