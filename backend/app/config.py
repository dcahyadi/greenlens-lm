import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # LLM
    OPENROUTER_API_KEY: str = ""
    LLM_MODEL: str = "openai/gpt-oss-20b:free"
    LLM_TEMPERATURE: float = 0.1
    LLM_MAX_TOKENS: int = 1024

    # Embeddings
    EMBEDDING_MODEL: str = "BAAI/bge-m3"

    # HuggingFace Hub token — optional, raises anonymous rate limits when
    # downloading/checking the embedding model.
    HF_TOKEN: str = ""

    # Storage
    CHROMA_PATH: str = "./chroma_db"
    DOCS_PATH: str = "../data/documents"

    # Optional: download a pre-built ChromaDB zip on startup if CHROMA_PATH
    # is empty. Used in production (Render free tier) instead of a paid
    # persistent disk. Leave blank for local dev — local dev already has
    # chroma_db/ populated from running ingestion/indexer.py directly.
    CHROMA_DB_DOWNLOAD_URL: str = ""

    # RAG
    RETRIEVER_K: int = 5
    CHUNK_SIZE: int = 1000
    CHUNK_OVERLAP: int = 150

    # API
    ALLOWED_ORIGINS: str = "http://localhost:5173,http://localhost:3000"
    ENVIRONMENT: str = "development"
    LOG_LEVEL: str = "INFO"

    # Rate limiting — max requests per 60s window, per client IP, on /api/query
    RATE_LIMIT_PER_MINUTE: int = 20

@lru_cache()
def get_settings() -> Settings:
    return Settings()


settings = get_settings()

# huggingface_hub checks os.environ directly, not our pydantic Settings
# object. Propagate HF_TOKEN here so a value from .env actually takes
# effect for model downloads, regardless of whether it was set via .env,
# a real `export`, or Render's dashboard environment variables.
if settings.HF_TOKEN:
    os.environ.setdefault("HF_TOKEN", settings.HF_TOKEN)