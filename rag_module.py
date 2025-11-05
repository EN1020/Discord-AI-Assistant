import os, pickle, asyncio, aiohttp, json, csv
from pathlib import Path
from typing import List, Dict, Optional, Tuple
import numpy as np
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
CHAT_MODEL = os.getenv("OPENAI_CHAT_MODEL", "gpt-4o-mini")           # 生成用
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")  # 嵌入用
INDEX_DIR = Path(os.getenv("RAG_INDEX_DIR", "E:/python/discord-ai-bot/rag_store"))
VEC_PATH = INDEX_DIR / "vectors.npy"
META_PATH = INDEX_DIR / "meta.pkl"

def _l2_normalize(v: np.ndarray) -> np.ndarray:
    return v / (np.linalg.norm(v) + 1e-12)

class RAG:
    def __init__(self):
        if not VEC_PATH.exists() or not META_PATH.exists():
            self.X = None
            self.meta = []
            return
        # 向量已在建索引時做 normalize；此處保險再轉 float32
        self.X = np.load(VEC_PATH).astype("float32")   # shape (N, D)
        with open(META_PATH, "rb") as f:
            # rag_index.py 儲存的是 list[dict]，每筆至少包含：
            # { "id", "text", "meta": { "source","type","path","raw":{question,answer,keywords_zh,keywords_en,tags} } }
            self.meta: List[Dict] = pickle.load(f)

    async def embed(self, text: str) -> List[float]:
        url = "https://api.openai.com/v1/embeddings"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {"model": EMBED_MODEL, "input": text}
        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers=headers, json=payload, timeout=60) as r:
                data = await r.json()
                v = np.array(data["data"][0]["embedding"], dtype="float32")
                v = _l2_normalize(v)
                return v.tolist()

    def _search(self, q_vec: List[float], k: int = 5) -> List[Tuple[Dict, float, int]]:
        """回傳 [(record, score, index_in_corpus), ...] 內積分數=cosine（皆已正規化）"""
        if self.X is None or not self.meta:
            return []
        q = np.array(q_vec, dtype="float32")
        q = _l2_normalize(q)
        scores = self.X @ q                                   # (N,)
        idx = np.argsort(-scores)[:k]
        return [(self.meta[i], float(scores[i]), int(i)) for i in idx]

    async def search(self, query: str, k: int = 5) -> List[Dict]:
        """對外：輸入 query，得到前 k 筆、含 question/answer 等的結構化結果"""
        v = await self.embed(query)
        hits = self._search(v, k)
        results = []
        for rec, score, i in hits:
            raw = ((rec.get("meta") or {}).get("raw") or {})
            results.append({
                "score": score,
                "id": rec.get("id"),
                "text": rec.get("text") or rec.get("content") or "",
                "source": (rec.get("meta") or {}).get("source"),
                "path":   (rec.get("meta") or {}).get("path"),
                "question": raw.get("question"),
                "answer":   raw.get("answer"),
                "keywords_zh": raw.get("keywords_zh"),
                "keywords_en": raw.get("keywords_en"),
                "tags": raw.get("tags"),
                "_idx": i,
            })
        return results

    async def retrieve(self, query: str, k: int = 5) -> List[Dict]:
        """向下相容舊介面：回傳 path + text（原本叫 content）」"""
        hits = await self.search(query, k)
        out = []
        for h in hits:
            out.append({
                "score": h["score"],
                "path": h["path"] or h["source"] or h["id"],
                "content": h["text"][:1000],   # 舊版字段名 content，截斷避免過長
                "question": h.get("question"),
            })
        return out

    async def suggest(self, query: str, threshold: float = 0.82) -> Optional[Dict]:
        """
        產生「你是不是想問：{question}？」的建議。
        回傳 {question, score} 或 None
        """
        hits = await self.search(query, k=1)
        if not hits:
            return None
        top = hits[0]
        q = top.get("question")
        if q and top["score"] >= threshold:
            # 簡單避免重覆：若使用者已包含題目，就不建議
            if q.strip() not in query:
                return {"question": q, "score": top["score"]}
        return None

    async def answer(self, query: str, confirm_if_match: bool = True) -> str:
        """
        confirm_if_match=True：若找到高相似度 FAQ 題目，會直接回覆『你是不是想問：xxx？』
        否則用 RAG context 正常作答。
        """
        if confirm_if_match:
            sug = await self.suggest(query)
            if sug:
                return f"你是不是想問：**{sug['question']}**？（信心={sug['score']:.2f}）\n回覆「是」我就用這題來回答，或直接輸入你的完整問題。"

        # 若無需先確認，或沒有建議，就組 RAG context 正常回答
        ctxs = await self.retrieve(query, k=4)
        context_text = "\n\n".join([f"[{c['path']}]\n{c['content']}" for c in ctxs])

        system = (
            "You are a helpful assistant. Use the provided CONTEXT to answer. "
            "If the answer isn't in the context, say you don't know and avoid fabricating."
        )
        user = f"QUESTION:\n{query}\n\nCONTEXT:\n{context_text}"

        url = "https://api.openai.com/v1/chat/completions"
        headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
        payload = {
            "model": CHAT_MODEL,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        async with aiohttp.ClientSession() as s:
            async with s.post(url, headers=headers, json=payload, timeout=60) as r:
                data = await r.json()
                return data["choices"][0]["message"]["content"].strip()
