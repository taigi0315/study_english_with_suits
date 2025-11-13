"""
Tests for file management API endpoints.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from langflix.api.dependencies import get_storage
from langflix.api.main import app
from langflix.storage.local import LocalStorage


@pytest.fixture
def storage_root(tmp_path: Path) -> Path:
    """Return isolated storage directory for each test."""
    root = tmp_path / "storage"
    root.mkdir(parents=True, exist_ok=True)
    return root


@pytest.fixture
def storage_backend(storage_root: Path) -> LocalStorage:
    """Instantiate LocalStorage backend for tests."""
    return LocalStorage(storage_root)


@pytest.fixture
def api_client(storage_backend: LocalStorage):
    """Provide FastAPI client with storage dependency override."""
    app.dependency_overrides[get_storage] = lambda: storage_backend
    client = TestClient(app)
    yield client
    app.dependency_overrides.pop(get_storage, None)


def _write_file(path: Path, content: str = "sample") -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content)


def test_list_files_returns_metadata(api_client: TestClient, storage_root: Path) -> None:
    file_path = storage_root / "folder" / "sample.txt"
    _write_file(file_path, "hello world")

    response = api_client.get("/api/v1/files")
    assert response.status_code == 200

    payload = response.json()
    assert payload["total"] == 1
    assert len(payload["files"]) == 1

    entry = payload["files"][0]
    assert entry["path"] == "folder/sample.txt"
    assert entry["name"] == "sample.txt"
    assert entry["size"] == file_path.stat().st_size
    assert entry["type"] == "text/plain"
    assert entry["url"].endswith("folder/sample.txt")


def test_get_file_details_returns_metadata(api_client: TestClient, storage_root: Path) -> None:
    file_path = storage_root / "video" / "clip.mp4"
    _write_file(file_path, "video-bytes")

    response = api_client.get("/api/v1/files/video/clip.mp4")
    assert response.status_code == 200

    payload = response.json()
    assert payload["file_id"] == "video/clip.mp4"
    assert payload["name"] == "clip.mp4"
    assert payload["size"] == file_path.stat().st_size
    assert payload["type"] == "video/mp4"


def test_get_file_details_not_found(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/files/missing/file.txt")
    assert response.status_code == 404
    payload = response.json()
    assert "File not found" in payload["error"]


def test_get_file_details_invalid_path(api_client: TestClient) -> None:
    response = api_client.get("/api/v1/files/%2E%2E/secrets.env")
    assert response.status_code == 400
    payload = response.json()
    assert "Path traversal" in payload["error"]


def test_delete_file_removes_file(api_client: TestClient, storage_root: Path) -> None:
    file_path = storage_root / "output" / "data.json"
    _write_file(file_path, '{"value": 1}')
    assert file_path.exists()

    response = api_client.delete("/api/v1/files/output/data.json")
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert not file_path.exists()


def test_delete_file_protected_pattern(api_client: TestClient, storage_root: Path) -> None:
    protected_file = storage_root / "config.yaml"
    _write_file(protected_file, "key: value")

    response = api_client.delete("/api/v1/files/config.yaml")
    assert response.status_code == 403
    payload = response.json()
    assert "Cannot delete protected file" in payload["error"]
    assert protected_file.exists()


def test_delete_directory_blocked(api_client: TestClient, storage_root: Path) -> None:
    directory_path = storage_root / "folder"
    directory_path.mkdir(parents=True, exist_ok=True)
    # Ensure directory is reported by file_exists
    response = api_client.delete("/api/v1/files/folder")
    assert response.status_code == 400
    payload = response.json()
    assert "Deleting directories is not supported" in payload["error"]


