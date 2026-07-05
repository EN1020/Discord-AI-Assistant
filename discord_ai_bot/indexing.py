from __future__ import annotations

import asyncio
import csv
import hashlib
import json
import pickle
import re
from pathlib import Path
from typing import Any

import numpy as np
from openai import OpenAI
from pypdf import PdfReader

from .config import Settings, load_settings


def read_txt(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def read_pdf(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def read_json_file(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8", errors="ignore"))
    return data if isinstance(data, list) else [data]


def read_csv_file(path: Path) -> list[dict[str, Any]]:
    with path.open("r", encoding="utf-8", newline="") as file:
        return list(csv.DictReader(file))


def rec_to_text(record: dict[str, Any]) -> str:
    question = record.get("question")
    answer = record.get("answer")
    if question and answer:
        extra: list[str] = []
        for key in ("keywords_zh", "keywords_en", "tags"):
            value = record.get(key)
            if value:
                extra.append(f"{key}: {_flatten(value)}")
        extra_text = ("\n" + "\n".join(extra)) if extra else ""
        return f"Q: {question}\nA: {answer}{extra_text}"
    return json.dumps(record, ensure_ascii=False)


def chunk_text(text: str, max_chars: int = 1200, overlap: int = 180) -> list[str]:
    normalized = re.sub(r"\n{3,}", "\n\n", text.strip())
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    chunks: list[str] = []
    start = 0
    while start < len(normalized):
        end = min(start + max_chars, len(normalized))
        cut = normalized.rfind("\n\n", start, end)
        if cut <= start + max_chars // 2:
            cut = normalized.rfind("\n", start, end)
        if cut <= start + max_chars // 2:
            cut = end
        chunk = normalized[start:cut].strip()
        if chunk:
            chunks.append(chunk)
        if cut >= len(normalized):
            break
        start = max(cut - overlap, start + 1)
    return chunks


def load_docs(
    docs_dir: Path | None = None,
    chunk_chars: int = 1200,
    chunk_overlap: int = 180,
) -> list[dict[str, Any]]:
    settings = load_settings()
    root = docs_dir or settings.docs_dir
    items: list[dict[str, Any]] = []
    seen: set[str] = set()

    for path in sorted(root.glob("**/*")):
        if path.is_dir():
            continue
        suffix = path.suffix.lower()
        try:
            if suffix == ".txt":
                _append_text_chunks(items, seen, path, read_txt(path), "txt", chunk_chars, chunk_overlap)
            elif suffix == ".pdf":
                _append_text_chunks(items, seen, path, read_pdf(path), "pdf", chunk_chars, chunk_overlap)
            elif suffix in {".json", ".jsonl", ".csv"}:
                records = _read_records(path, suffix)
                for index, record in enumerate(records, start=1):
                    record_id = record.get("id") or f"{path.stem}__{index:03d}"
                    text = rec_to_text(record)
                    _append_item(
                        items,
                        seen,
                        {
                            "id": str(record_id),
                            "text": text,
                            "meta": {
                                "source": path.name,
                                "type": suffix.lstrip("."),
                                "path": str(path),
                                "raw": {
                                    "question": record.get("question"),
                                    "answer": record.get("answer"),
                                    "keywords_zh": record.get("keywords_zh"),
                                    "keywords_en": record.get("keywords_en"),
                                    "tags": record.get("tags"),
                                },
                            },
                        },
                    )
        except Exception as exc:
            print(f"[load_docs] Skip {path.name}: {exc}")

    return items


async def embed_texts(
    texts: list[str],
    settings: Settings | None = None,
    client: OpenAI | None = None,
) -> list[list[float]]:
    cfg = settings or load_settings()
    openai_client = client or OpenAI(api_key=cfg.openai_api_key)
    vectors: list[list[float]] = []
    batch_size = max(1, cfg.embed_batch_size)

    for start in range(0, len(texts), batch_size):
        batch = texts[start : start + batch_size]
        response = await asyncio.to_thread(
            openai_client.embeddings.create,
            model=cfg.embed_model,
            input=batch,
        )
        vectors.extend([item.embedding for item in response.data])
    return vectors


def save_index(records: list[dict[str, Any]], vectors: list[list[float]], settings: Settings) -> None:
    settings.index_dir.mkdir(parents=True, exist_ok=True)
    matrix = np.array(vectors, dtype="float32")
    matrix /= np.linalg.norm(matrix, axis=1, keepdims=True) + 1e-12
    np.save(settings.vectors_path, matrix)

    settings.metadata_json_path.write_text(
        json.dumps(records, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    with settings.metadata_pickle_path.open("wb") as file:
        pickle.dump(records, file)


async def main() -> None:
    settings = load_settings()
    count = await build_index(settings)
    if count == 0:
        print("No docs found. Put PDF/TXT/JSON/CSV files into ./docs then rerun.")


async def build_index(settings: Settings) -> int:
    if not settings.openai_api_key:
        raise RuntimeError("Missing OPENAI_API_KEY")

    print(f"Loading docs from {settings.docs_dir} ...")
    records = load_docs(
        settings.docs_dir,
        chunk_chars=settings.rag_chunk_chars,
        chunk_overlap=settings.rag_chunk_overlap,
    )
    if not records:
        return 0

    print(f"Total records: {len(records)}")
    print("Embedding ...")
    vectors = await embed_texts([item["text"] for item in records], settings=settings)

    print("Saving index ...")
    save_index(records, vectors, settings)
    print(f"Done. Vectors: {settings.vectors_path} Metadata: {settings.metadata_json_path}")
    return len(records)


def _read_records(path: Path, suffix: str) -> list[dict[str, Any]]:
    if suffix == ".jsonl":
        return read_jsonl(path)
    if suffix == ".json":
        return read_json_file(path)
    return read_csv_file(path)


def _append_text_chunks(
    items: list[dict[str, Any]],
    seen: set[str],
    path: Path,
    text: str,
    file_type: str,
    chunk_chars: int,
    chunk_overlap: int,
) -> None:
    chunks = chunk_text(text, max_chars=chunk_chars, overlap=chunk_overlap)
    for index, chunk in enumerate(chunks, start=1):
        item_id = path.name if len(chunks) == 1 else f"{path.name}#{index:03d}"
        _append_item(
            items,
            seen,
            {
                "id": item_id,
                "text": chunk,
                "meta": {
                    "source": path.name,
                    "type": file_type,
                    "path": str(path),
                    "chunk": index,
                },
            },
        )


def _append_item(items: list[dict[str, Any]], seen: set[str], item: dict[str, Any]) -> None:
    text = item.get("text") or ""
    item_id = item.get("id")
    id_key = f"id:{item_id}" if item_id else None
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    text_key = f"text:{digest}"
    if (id_key and id_key in seen) or text_key in seen:
        return
    if id_key:
        seen.add(id_key)
    seen.add(text_key)
    items.append(item)


def _flatten(value: Any) -> str:
    if isinstance(value, str):
        return value
    if isinstance(value, (list, tuple)):
        return ", ".join(str(item) for item in value)
    return str(value)
