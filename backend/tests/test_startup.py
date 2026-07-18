"""
GreenLens LM — tests for app/startup.py

This module is what the entire production deployment depends on since we
moved off a paid persistent disk (see docs/design-and-testing.md, section
2.12). It downloads and extracts a pre-built ChromaDB archive on cold
start. These tests protect that behavior from silent regressions.
"""
import io
import zipfile
from unittest.mock import MagicMock, patch

import pytest

import app.startup as startup_module
from app.config import Settings
from app.startup import _chroma_has_data, ensure_chroma_data


def make_zip_bytes(files: dict) -> bytes:
    """Build an in-memory zip archive from {relative_path: content_bytes}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    return buf.getvalue()


# ── _chroma_has_data ──────────────────────────────────────────────────────

def test_chroma_has_data_false_for_empty_dir(tmp_path):
    assert _chroma_has_data(tmp_path) is False


def test_chroma_has_data_true_when_sqlite_present(tmp_path):
    (tmp_path / "chroma.sqlite3").touch()
    assert _chroma_has_data(tmp_path) is True


def test_chroma_has_data_false_for_nonexistent_dir(tmp_path):
    missing = tmp_path / "does_not_exist_yet"
    assert _chroma_has_data(missing) is False


# ── ensure_chroma_data ────────────────────────────────────────────────────

def test_ensure_chroma_data_skips_download_when_data_already_exists(tmp_path, monkeypatch):
    """Local dev, or any environment where data is already populated,
    must never trigger a network call."""
    (tmp_path / "chroma.sqlite3").touch()
    test_settings = Settings(
        CHROMA_PATH=str(tmp_path),
        CHROMA_DB_DOWNLOAD_URL="http://example.invalid/should-not-be-called.zip",
    )
    monkeypatch.setattr(startup_module, "settings", test_settings)

    with patch("httpx.Client") as mock_client:
        ensure_chroma_data()
        mock_client.assert_not_called()


def test_ensure_chroma_data_warns_when_empty_and_no_url_configured(tmp_path, monkeypatch):
    """No download URL and no local data — should warn, not crash, and
    not attempt any network call."""
    empty_dir = tmp_path / "empty_chroma"
    test_settings = Settings(
        CHROMA_PATH=str(empty_dir),
        CHROMA_DB_DOWNLOAD_URL="",
    )
    monkeypatch.setattr(startup_module, "settings", test_settings)

    with patch("httpx.Client") as mock_client:
        ensure_chroma_data()
        mock_client.assert_not_called()

    assert not (empty_dir / "chroma.sqlite3").exists()


def test_ensure_chroma_data_downloads_and_extracts_archive(tmp_path, monkeypatch):
    """The core production path: empty CHROMA_PATH + a configured URL
    should download, then correctly extract nested directory structure."""
    target_dir = tmp_path / "chroma_download_target"
    zip_bytes = make_zip_bytes({
        "chroma.sqlite3": b"fake sqlite content",
        "some_collection_dir/data.bin": b"fake vector data",
    })

    test_settings = Settings(
        CHROMA_PATH=str(target_dir),
        CHROMA_DB_DOWNLOAD_URL="http://example.invalid/chroma_db.zip",
    )
    monkeypatch.setattr(startup_module, "settings", test_settings)

    mock_response = MagicMock()
    mock_response.content = zip_bytes
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.__exit__.return_value = False

    with patch("httpx.Client", return_value=mock_client_instance):
        ensure_chroma_data()

    assert (target_dir / "chroma.sqlite3").exists()
    assert (target_dir / "some_collection_dir" / "data.bin").exists()
    assert (target_dir / "chroma.sqlite3").read_bytes() == b"fake sqlite content"
    assert (target_dir / "some_collection_dir" / "data.bin").read_bytes() == b"fake vector data"


def test_ensure_chroma_data_calls_correct_url(tmp_path, monkeypatch):
    """Confirm the exact configured URL is requested — protects against
    a typo or stale hardcoded value silently pointing at the wrong asset."""
    target_dir = tmp_path / "chroma_url_check"
    zip_bytes = make_zip_bytes({"chroma.sqlite3": b"x"})
    expected_url = "http://example.invalid/chroma-db-v1/chroma_db.zip"

    test_settings = Settings(
        CHROMA_PATH=str(target_dir),
        CHROMA_DB_DOWNLOAD_URL=expected_url,
    )
    monkeypatch.setattr(startup_module, "settings", test_settings)

    mock_response = MagicMock()
    mock_response.content = zip_bytes
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.__exit__.return_value = False

    with patch("httpx.Client", return_value=mock_client_instance):
        ensure_chroma_data()

    mock_client_instance.get.assert_called_once_with(expected_url)


def test_ensure_chroma_data_raises_on_download_failure(tmp_path, monkeypatch):
    """A failed download must raise (and be logged), not fail silently —
    a silently-empty ChromaDB would make every query return no sources
    instead of a clear startup error."""
    target_dir = tmp_path / "chroma_fail_target"
    test_settings = Settings(
        CHROMA_PATH=str(target_dir),
        CHROMA_DB_DOWNLOAD_URL="http://example.invalid/chroma_db.zip",
    )
    monkeypatch.setattr(startup_module, "settings", test_settings)

    mock_client_instance = MagicMock()
    mock_client_instance.get.side_effect = Exception("Connection failed")
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.__exit__.return_value = False

    with patch("httpx.Client", return_value=mock_client_instance):
        with pytest.raises(Exception, match="Connection failed"):
            ensure_chroma_data()


def test_ensure_chroma_data_raises_on_corrupt_zip(tmp_path, monkeypatch):
    """A downloaded file that isn't a valid zip (e.g. GitHub Releases
    returned an HTML error page instead of the asset) must raise clearly
    rather than leave a partially-extracted, confusing state."""
    target_dir = tmp_path / "chroma_corrupt_target"
    test_settings = Settings(
        CHROMA_PATH=str(target_dir),
        CHROMA_DB_DOWNLOAD_URL="http://example.invalid/chroma_db.zip",
    )
    monkeypatch.setattr(startup_module, "settings", test_settings)

    mock_response = MagicMock()
    mock_response.content = b"<html>Not Found</html>"  # not a valid zip
    mock_response.raise_for_status = MagicMock()

    mock_client_instance = MagicMock()
    mock_client_instance.get.return_value = mock_response
    mock_client_instance.__enter__.return_value = mock_client_instance
    mock_client_instance.__exit__.return_value = False

    with patch("httpx.Client", return_value=mock_client_instance):
        with pytest.raises(Exception):
            ensure_chroma_data()
