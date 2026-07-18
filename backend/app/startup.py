"""
GreenLens LM — Startup data provisioning.

On platforms without a persistent disk (e.g. Render's free tier), the
container filesystem is wiped on every deploy and every cold start. This
module downloads a pre-built ChromaDB archive (produced once, locally, via
`python ingestion/indexer.py`) and extracts it into CHROMA_PATH before the
app starts serving requests — avoiding the need for a paid disk or a slow
re-embedding step at build time.

If CHROMA_PATH already contains data (e.g. local dev, or a future setup
that does use a persistent disk), this is a no-op.
"""

import io
import zipfile
from pathlib import Path

import httpx
from loguru import logger

from app.config import settings


def _chroma_has_data(chroma_path: Path) -> bool:
    """ChromaDB's persistent client always creates a chroma.sqlite3 file."""
    return (chroma_path / "chroma.sqlite3").exists()


def ensure_chroma_data() -> None:
    """
    Ensure CHROMA_PATH is populated before the app starts handling requests.
    Downloads and extracts CHROMA_DB_DOWNLOAD_URL if CHROMA_PATH is empty
    and a download URL is configured.
    """
    chroma_path = Path(settings.CHROMA_PATH)

    if _chroma_has_data(chroma_path):
        logger.info(f"ChromaDB data already present at {chroma_path} — skipping download")
        return

    if not settings.CHROMA_DB_DOWNLOAD_URL:
        logger.warning(
            f"ChromaDB path {chroma_path} is empty and no CHROMA_DB_DOWNLOAD_URL "
            "is configured. Run 'python ingestion/indexer.py' locally, or set "
            "CHROMA_DB_DOWNLOAD_URL to fetch a pre-built archive."
        )
        return

    logger.info(f"Downloading ChromaDB archive from {settings.CHROMA_DB_DOWNLOAD_URL}")
    try:
        with httpx.Client(follow_redirects=True, timeout=120.0) as client:
            response = client.get(settings.CHROMA_DB_DOWNLOAD_URL)
            response.raise_for_status()

        chroma_path.mkdir(parents=True, exist_ok=True)

        with zipfile.ZipFile(io.BytesIO(response.content)) as zf:
            zf.extractall(chroma_path)

        logger.info(f"ChromaDB archive extracted to {chroma_path}")

    except Exception as e:
        logger.error(f"Failed to download/extract ChromaDB archive: {e}")
        raise
