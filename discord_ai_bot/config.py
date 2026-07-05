from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv

WebSearchMode = Literal["off", "auto", "always"]


def _env_int(name: str, default: int) -> int:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _env_float(name: str, default: float) -> float:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    try:
        return float(value)
    except ValueError:
        return default


def _env_bool(name: str, default: bool) -> bool:
    value = os.getenv(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _csv_env(name: str) -> tuple[str, ...]:
    value = os.getenv(name, "")
    return tuple(part.strip() for part in value.split(",") if part.strip())


def _web_mode(value: str | None) -> WebSearchMode:
    normalized = (value or "auto").strip().lower()
    if normalized in {"off", "auto", "always"}:
        return normalized  # type: ignore[return-value]
    return "auto"


@dataclass(frozen=True)
class Settings:
    discord_token: str | None
    openai_api_key: str | None
    chat_model: str
    web_model: str
    embed_model: str
    system_prompt: str
    docs_dir: Path
    index_dir: Path
    memory_messages: int
    discord_message_limit: int
    web_search_mode: WebSearchMode
    web_search_live: bool
    web_search_allowed_domains: tuple[str, ...]
    web_search_blocked_domains: tuple[str, ...]
    user_location_country: str | None
    user_location_city: str | None
    user_location_region: str | None
    user_location_timezone: str | None
    rag_top_k: int
    rag_min_score: float
    rag_suggest_threshold: float
    rag_context_chars: int
    rag_chunk_chars: int
    rag_chunk_overlap: int
    embed_batch_size: int
    auto_build_rag_on_start: bool

    @property
    def vectors_path(self) -> Path:
        return self.index_dir / "vectors.npy"

    @property
    def metadata_json_path(self) -> Path:
        return self.index_dir / "meta.json"

    @property
    def metadata_pickle_path(self) -> Path:
        return self.index_dir / "meta.pkl"

    def validate_runtime(self) -> None:
        missing = []
        if not self.discord_token:
            missing.append("DISCORD_TOKEN")
        if not self.openai_api_key:
            missing.append("OPENAI_API_KEY")
        if missing:
            names = " and ".join(missing)
            raise RuntimeError(f"Missing required environment variable(s): {names}")


def load_settings() -> Settings:
    load_dotenv()
    chat_model = (
        os.getenv("OPENAI_CHAT_MODEL")
        or os.getenv("OPENAI_MODEL")
        or "gpt-4o-mini"
    )
    return Settings(
        discord_token=os.getenv("DISCORD_TOKEN"),
        openai_api_key=os.getenv("OPENAI_API_KEY"),
        chat_model=chat_model,
        web_model=os.getenv("OPENAI_WEB_MODEL") or chat_model,
        embed_model=os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small"),
        system_prompt=os.getenv("SYSTEM_PROMPT", "You are a helpful assistant."),
        docs_dir=Path(os.getenv("DOCS_DIR", "./docs")),
        index_dir=Path(os.getenv("RAG_INDEX_DIR", "./rag_store")),
        memory_messages=_env_int("CONVERSATION_MEMORY_MESSAGES", 16),
        discord_message_limit=_env_int("DISCORD_MESSAGE_LIMIT", 1900),
        web_search_mode=_web_mode(os.getenv("WEB_SEARCH_MODE")),
        web_search_live=_env_bool("WEB_SEARCH_LIVE", True),
        web_search_allowed_domains=_csv_env("WEB_SEARCH_ALLOWED_DOMAINS"),
        web_search_blocked_domains=_csv_env("WEB_SEARCH_BLOCKED_DOMAINS"),
        user_location_country=os.getenv("USER_LOCATION_COUNTRY") or "TW",
        user_location_city=os.getenv("USER_LOCATION_CITY") or None,
        user_location_region=os.getenv("USER_LOCATION_REGION") or None,
        user_location_timezone=os.getenv("USER_LOCATION_TIMEZONE") or "Asia/Taipei",
        rag_top_k=_env_int("RAG_TOP_K", 5),
        rag_min_score=_env_float("RAG_MIN_SCORE", 0.2),
        rag_suggest_threshold=_env_float("RAG_SUGGEST_THRESHOLD", 0.82),
        rag_context_chars=_env_int("RAG_CONTEXT_CHARS", 1200),
        rag_chunk_chars=_env_int("RAG_CHUNK_CHARS", 1200),
        rag_chunk_overlap=_env_int("RAG_CHUNK_OVERLAP", 180),
        embed_batch_size=_env_int("EMBED_BATCH_SIZE", 64),
        auto_build_rag_on_start=_env_bool("AUTO_BUILD_RAG_ON_START", False),
    )
