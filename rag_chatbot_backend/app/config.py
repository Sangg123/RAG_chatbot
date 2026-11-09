import json
from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import parse_qsl, urlencode

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore") # cho phép biến dư 

    app_name: str = "RAG Chatbot Backend"
    environment: str = "development"
    api_v1_prefix: str = "/api/v1"
    backend_cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    database_url: str

    # Backward-compatible with older .env files.
    default_user_id: str | None = None

    jwt_secret_key: str
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 30
    refresh_token_expire_days: int = 7

    admin_seed_user_id: str = "00000000-0000-0000-0000-000000000001"
    admin_seed_username: str = "admin"
    admin_seed_email: str = "admin@company.com"
    admin_seed_password: str = "admin123"

    gemini_api_key: str
    gemini_chat_model: str = "gemini-3.5-flash"
    gemini_title_model: str = "gemini-3.1-flash-lite"
    # Comma-separated models tried in order when the primary model is
    # overloaded/unavailable (e.g. 503 "high demand").
    gemini_fallback_models: str = "gemini-3.1-flash-lite"

    # "ollama" keeps local development unchanged. Use "gemini" on free hosts
    # that cannot run a local embedding model (e.g. Render 512 MB RAM).
    embedding_provider: Literal["ollama", "gemini"] = "ollama"
    gemini_embed_model: str = "gemini-embedding-001"
    # gemini-embedding-001 supports 128..3072. 1536 is a good size/quality
    # trade-off and intentionally differs from embeddinggemma's 768 dims, so
    # old local vectors are ignored by the vector_dims filter instead of
    # producing misleading similarity scores.
    gemini_embed_dim: int = 1536
    gemini_embed_batch_size: int = 50
    gemini_embed_max_retries: int = 3

    ollama_base_url: str = "http://localhost:11434"
    ollama_embed_model: str = "embeddinggemma"

    chunk_size: int = 1000
    chunk_overlap: int = 200
    semantic_chunking_enabled: bool = True
    semantic_similarity_threshold: float = 0.22
    semantic_min_sentences_per_chunk: int = 2
    top_k_chunks: int = 5

    storage_dir: str = "storage/uploads"
    # None/0 keeps the previous local behavior (no application-level limit).
    # Set MAX_UPLOAD_MB=20 on Render to protect the 512 MB instance.
    max_upload_mb: int | None = None
    allow_public_registration: bool = True

    @field_validator("database_url", mode="before")
    @classmethod
    def normalize_database_url(cls, v: str) -> str:
        """Accept a plain Neon/Postgres URL and use the asyncpg driver."""
        if not isinstance(v, str):
            return v

        if v.startswith("postgres://"):
            v = "postgresql+asyncpg://" + v[len("postgres://") :]
        elif v.startswith("postgresql://"):
            v = "postgresql+asyncpg://" + v[len("postgresql://") :]

        # Neon's copy button emits libpq parameters (sslmode, channel_binding)
        # that asyncpg's SQLAlchemy dialect does not accept as connect args.
        if "?" in v:
            base, _, query = v.partition("?")
            params = [
                ("ssl" if key == "sslmode" else key, value)
                for key, value in parse_qsl(query, keep_blank_values=True)
                if key != "channel_binding"
            ]
            v = base + ("?" + urlencode(params) if params else "")
        return v

    @field_validator("backend_cors_origins", mode="before")
    @classmethod
    def split_cors(cls, v: str | list[str]) -> list[str]:
        if isinstance(v, str):
            value = v.strip()
            if value.startswith("["):
                return json.loads(value)
            return [item.strip() for item in value.split(",") if item.strip()]
        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
