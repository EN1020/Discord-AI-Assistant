from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class Source:
    title: str
    url: str


def to_plain_data(value: Any) -> Any:
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, list):
        return [to_plain_data(item) for item in value]
    if isinstance(value, tuple):
        return [to_plain_data(item) for item in value]
    if isinstance(value, dict):
        return {str(key): to_plain_data(item) for key, item in value.items()}
    if hasattr(value, "model_dump"):
        return to_plain_data(value.model_dump())
    if hasattr(value, "dict"):
        return to_plain_data(value.dict())
    return value


def extract_output_text(response: Any) -> str:
    text = getattr(response, "output_text", None)
    if text:
        return str(text).strip()

    data = to_plain_data(response)
    chunks: list[str] = []

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if value.get("type") in {"output_text", "text"} and value.get("text"):
                chunks.append(str(value["text"]))
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(data)
    return "".join(chunks).strip()


def collect_sources(response: Any) -> list[Source]:
    data = to_plain_data(response)
    found: list[Source] = []

    def add_source(raw: dict[str, Any]) -> None:
        url = raw.get("url") or raw.get("uri")
        if not url:
            return
        title = raw.get("title") or raw.get("name") or str(url)
        found.append(Source(title=str(title), url=str(url)))

    def walk(value: Any) -> None:
        if isinstance(value, dict):
            if isinstance(value.get("sources"), list):
                for source in value["sources"]:
                    if isinstance(source, dict):
                        add_source(source)
            if value.get("type") in {"url_citation", "citation"}:
                add_source(value)
            for key in ("annotations", "citations"):
                if isinstance(value.get(key), list):
                    for item in value[key]:
                        if isinstance(item, dict):
                            walk(item)
            for item in value.values():
                walk(item)
        elif isinstance(value, list):
            for item in value:
                walk(item)

    walk(data)

    deduped: list[Source] = []
    seen: set[str] = set()
    for source in found:
        if source.url in seen:
            continue
        seen.add(source.url)
        deduped.append(source)
    return deduped
