from __future__ import annotations

import asyncio
import json
import pickle
from dataclasses import dataclass
from typing import Any

import numpy as np
from openai import OpenAI, OpenAIError

from .config import Settings, load_settings
from .openai_utils import extract_output_text


def _l2_normalize(vector: np.ndarray) -> np.ndarray:
    return vector / (np.linalg.norm(vector) + 1e-12)


@dataclass(frozen=True)
class RetrievedContext:
    score: float
    path: str
    content: str
    question: str | None = None
    answer: str | None = None


class RAG:
    def __init__(self, settings: Settings | None = None, client: OpenAI | None = None):
        self.settings = settings or load_settings()
        self.client = client or OpenAI(api_key=self.settings.openai_api_key)
        self.X: np.ndarray | None = None
        self.meta: list[dict[str, Any]] = []
        self.reload()

    def reload(self) -> None:
        if not self.settings.vectors_path.exists():
            self.X = None
            self.meta = []
            return
        self.X = np.load(self.settings.vectors_path).astype("float32")
        self.meta = self._load_metadata()

    def ready(self) -> bool:
        return self.X is not None and bool(self.meta)

    async def embed(self, text: str) -> list[float]:
        try:
            response = await asyncio.to_thread(
                self.client.embeddings.create,
                model=self.settings.embed_model,
                input=text,
            )
        except OpenAIError as exc:
            raise RuntimeError(f"OpenAI embeddings error: {exc.__class__.__name__}") from exc
        vector = np.array(response.data[0].embedding, dtype="float32")
        return _l2_normalize(vector).tolist()

    def _search(self, query_vector: list[float], k: int = 5) -> list[tuple[dict[str, Any], float, int]]:
        if self.X is None or not self.meta:
            return []
        q = _l2_normalize(np.array(query_vector, dtype="float32"))
        scores = self.X @ q
        indexes = np.argsort(-scores)[:k]
        return [(self.meta[i], float(scores[i]), int(i)) for i in indexes]

    async def search(
        self,
        query: str,
        k: int | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> list[dict[str, Any]]:
        if not self.ready():
            return []
        retrieval_query = self._contextual_query(query, history)
        vector = await self.embed(retrieval_query)
        hits = self._search(vector, k or self.settings.rag_top_k)
        results: list[dict[str, Any]] = []
        for record, score, index in hits:
            raw = ((record.get("meta") or {}).get("raw") or {})
            results.append(
                {
                    "score": score,
                    "id": record.get("id"),
                    "text": record.get("text") or record.get("content") or "",
                    "source": (record.get("meta") or {}).get("source"),
                    "path": (record.get("meta") or {}).get("path"),
                    "question": raw.get("question"),
                    "answer": raw.get("answer"),
                    "keywords_zh": raw.get("keywords_zh"),
                    "keywords_en": raw.get("keywords_en"),
                    "tags": raw.get("tags"),
                    "_idx": index,
                }
            )
        return results

    async def retrieve(
        self,
        query: str,
        k: int | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> list[RetrievedContext]:
        hits = await self.search(query, k=k, history=history)
        contexts: list[RetrievedContext] = []
        for hit in hits:
            if hit["score"] < self.settings.rag_min_score:
                continue
            path = hit["path"] or hit["source"] or hit["id"] or "unknown"
            contexts.append(
                RetrievedContext(
                    score=hit["score"],
                    path=str(path),
                    content=str(hit["text"])[: self.settings.rag_context_chars],
                    question=hit.get("question"),
                    answer=hit.get("answer"),
                )
            )
        return contexts

    async def suggest(self, query: str, threshold: float | None = None) -> dict[str, Any] | None:
        hits = await self.search(query, k=1)
        if not hits:
            return None
        top = hits[0]
        question = top.get("question")
        min_score = threshold if threshold is not None else self.settings.rag_suggest_threshold
        if question and top["score"] >= min_score and question.strip() not in query:
            return {"question": question, "score": top["score"]}
        return None

    async def answer(
        self,
        query: str,
        history: list[dict[str, str]] | None = None,
        confirm_if_match: bool = False,
    ) -> str:
        if confirm_if_match:
            suggestion = await self.suggest(query)
            if suggestion:
                return (
                    f"你是不是想問：**{suggestion['question']}**？"
                    f"（信心={suggestion['score']:.2f}）"
                )

        contexts = await self.retrieve(query, k=self.settings.rag_top_k, history=history)
        if not contexts:
            return "我在本地知識庫裡沒有找到足夠相關的資料，所以不硬猜。若你要查最新網路資訊，可以用 `/web` 或直接 `/ask`。"

        response = await asyncio.to_thread(
            self.client.responses.create,
            model=self.settings.chat_model,
            instructions=self._rag_instructions(),
            input=[
                {
                    "role": "user",
                    "content": self._rag_user_prompt(query, contexts, history),
                }
            ],
        )
        text = extract_output_text(response) or "(No text returned)"
        return f"{text}\n\n{self._format_context_sources(contexts)}"

    def _load_metadata(self) -> list[dict[str, Any]]:
        if self.settings.metadata_json_path.exists():
            return json.loads(self.settings.metadata_json_path.read_text(encoding="utf-8"))
        if self.settings.metadata_pickle_path.exists():
            with self.settings.metadata_pickle_path.open("rb") as file:
                return pickle.load(file)
        return []

    def _contextual_query(self, query: str, history: list[dict[str, str]] | None) -> str:
        recent = []
        for message in (history or [])[-4:]:
            content = message.get("content", "")
            if content:
                recent.append(f"{message.get('role', 'user')}: {content[:400]}")
        if not recent:
            return query
        return "Recent conversation:\n" + "\n".join(recent) + f"\n\nCurrent question:\n{query}"

    def _rag_instructions(self) -> str:
        return "\n".join(
            [
                "You are a careful RAG assistant.",
                "Answer in Traditional Chinese unless the user asks otherwise.",
                "Use only the provided context and recent conversation.",
                "If the answer is not supported by the context, say you do not know.",
            ]
        )

    def _rag_user_prompt(
        self,
        query: str,
        contexts: list[RetrievedContext],
        history: list[dict[str, str]] | None,
    ) -> str:
        conversation = "\n".join(
            f"{item.get('role')}: {item.get('content')}" for item in (history or [])[-6:]
        )
        context_text = "\n\n".join(
            f"[{index}] {ctx.path} (score={ctx.score:.2f})\n{ctx.content}"
            for index, ctx in enumerate(contexts, start=1)
        )
        return (
            f"RECENT CONVERSATION:\n{conversation or '(none)'}\n\n"
            f"QUESTION:\n{query}\n\n"
            f"CONTEXT:\n{context_text}"
        )

    def _format_context_sources(self, contexts: list[RetrievedContext]) -> str:
        lines = ["Local sources:"]
        seen: set[str] = set()
        for context in contexts:
            label = f"{context.path} (score={context.score:.2f})"
            if label in seen:
                continue
            seen.add(label)
            lines.append(f"- {label}")
        return "\n".join(lines)
