"""Configuration management using pydantic-settings."""

import json
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Database
    database_url: str = "postgresql://medwiss:changeme@localhost:5432/medwiss"

    # API
    api_version: str = "v1"
    app_env: str = "development"

    # CORS
    cors_origins: list[str] = ["http://localhost:5175", "http://localhost:3000"]

    # Embedding (CPU sidecar for query time; Qwen3-Embedding-8B Q6_K slice→normalize to 2048)
    embedding_url: str = "http://localhost:8081"
    embedding_dimension: int = 2048

    # Chunk search mode: "embed" = sidecar vectors (default, local);
    # "keyword" = tsvector full-text over chunks.search_vector, no sidecar
    # needed (VPS — 2 GB box cannot run the Qwen3-Embedding sidecar).
    chunk_search_mode: str = "embed"

    # LLM Provider
    llm_provider: str = "llamaserver"
    llamaserver_model: str = "qwen35-9b-i"
    llamaserver_url: str = "http://localhost:8080"
    llamaserver_api_key: str = ""
    openrouter_api_key: str = ""
    openrouter_default_model: str = "deepseek/deepseek-v4-flash"
    openrouter_fallback_model: str = "deepseek/deepseek-v4-flash"

    # On-demand OCR (image/PDF) — used ONLY by the summarize flow, never at
    # ingest. OCR_BACKENDS is an ordered, comma-separated list of backend
    # names tried in order; empty list == OCR unavailable (extract raises).
    #   tesseract         — local, needs tesseract+poppler (tux only)
    #   openrouter-vision — glm-4.6v vision via OpenRouter (remote, needs
    #                       OPENROUTER_API_KEY) — no separate OCR provider.
    ocr_backends: Annotated[list[str], NoDecode] = []
    openrouter_vision_model: str = "z-ai/glm-4.6v"
    # Timeouts / guards for remote OCR
    ocr_remote_timeout_seconds: int = 300
    ocr_max_pages: int = 30

    @field_validator("ocr_backends", mode="before")
    @classmethod
    def _parse_backends(cls, v):
        if v is None:
            return []
        if isinstance(v, str):
            s = v.strip()
            if not s:
                return []
            if s.startswith("["):  # JSON-array form if set as a plain env override
                parsed = json.loads(s)
                return [str(x).strip() for x in parsed]
            return [x.strip() for x in s.split(",") if x.strip()]
        return v

    # WHO ICD-11 API
    icd11_client_id: str = ""
    icd11_client_secret: str = ""

    # File Upload
    max_file_size_mb: int = 50
    api_timeout_seconds: int = 120
    # Write-through: when True, text-file entry edits are written back to the
    # source file on disk (env: FILE_WRITEBACK_ENABLED).
    file_writeback_enabled: bool = False


settings = Settings()
