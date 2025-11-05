import os, pickle, re, asyncio, aiohttp, json, csv
from pathlib import Path
from typing import List, Dict
from dotenv import load_dotenv
from pypdf import PdfReader
import numpy as np

load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
EMBED_MODEL = os.getenv("OPENAI_EMBED_MODEL", "text-embedding-3-small")
DOCS_DIR = Path(os.getenv("DOCS_DIR", "./docs"))
INDEX_DIR = Path(os.getenv("RAG_INDEX_DIR", "./rag_store"))
INDEX_DIR.mkdir(parents=True, exist_ok=True)

VEC_PATH = INDEX_DIR / "vectors.npy"
META_PATH = INDEX_DIR / "meta.pkl"

def read_txt(p: Path) -> str:
    return p.read_text(encoding="utf-8", errors="ignore")

def read_pdf(p: Path) -> str:
    r = PdfReader(str(p))
    return "\n".join(page.extract_text() or "" for page in r.pages)

def read_jsonl(p: Path):
    """讀取 .jsonl：每行一個 JSON 物件 -> List[Dict]"""
    lines = p.read_text(encoding="utf-8", errors="ignore").splitlines()
    return [json.loads(line) for line in lines if line.strip()]

def read_json_file(p: Path):
    """讀取 .json：整個檔是一個 JSON 結構（通常是 List[Dict] 或 Dict）"""
    return json.loads(p.read_text(encoding="utf-8", errors="ignore"))

def read_csv_file(p: Path):
    """讀取 .csv：以欄位名稱為 key -> List[Dict]"""
    rows = []
    with p.open("r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows

def rec_to_text(rec: dict) -> str:
    """
    將 FAQ 類資料（含 question/answer/keywords/tags）轉為可嵌入的文字。
    若沒有這些欄位，就 fallback 成整段 JSON。
    """
    q = rec.get("question")
    a = rec.get("answer")
    if q and a:
        # keywords / tags 可能來自你剛做的 with_keywords 版本
        kz = rec.get("keywords_zh")
        ke = rec.get("keywords_en")
        tags = rec.get("tags")

        def _flat(v):
            if v is None:
                return ""
            if isinstance(v, (list, tuple)):
                return ", ".join(map(str, v))
            return str(v)

        extra = []
        if kz:   extra.append(f"keywords_zh: {_flat(kz)}")
        if ke:   extra.append(f"keywords_en: {_flat(ke)}")
        if tags: extra.append(f"tags: {_flat(tags)}")

        extra_text = ("\n" + "\n".join(extra)) if extra else ""
        return f"Q: {q}\nA: {a}{extra_text}"
    # fallback：不是 FAQ 結構就直接轉字串
    return json.dumps(rec, ensure_ascii=False)


def load_docs() -> List[Dict]:
    items = []
    for p in DOCS_DIR.glob("**/*"):
        if p.is_dir():
            continue
        suffix = p.suffix.lower()

        # 純文字
        if suffix == ".txt":
            items.append({
                "id": f"{p.name}",
                "text": read_txt(p),
                "meta": {"source": p.name, "type": "txt", "path": str(p)}
            })
            continue

        # PDF
        if suffix == ".pdf":
            items.append({
                "id": f"{p.name}",
                "text": read_pdf(p),
                "meta": {"source": p.name, "type": "pdf", "path": str(p)}
            })
            continue

        # JSON / JSONL / CSV：逐筆轉成片段
        try:
            if suffix == ".jsonl":
                recs = read_jsonl(p)
            elif suffix == ".json":
                js = read_json_file(p)
                recs = js if isinstance(js, list) else [js]
            elif suffix == ".csv":
                recs = read_csv_file(p)
            else:
                # 不支援的副檔名就跳過
                continue

            for i, rec in enumerate(recs, 1):
                rid = rec.get("id") or f"{p.stem}__{i:03d}"
                text = rec_to_text(rec)
                items.append({
                    "id": rid,
                    "text": text,
                    "meta": {
                        "source": p.name,
                        "type": suffix.lstrip("."),
                        "path": str(p),
                        # 方便除錯／回顧
                        "raw": {
                            "question": rec.get("question"),
                            "answer": rec.get("answer"),
                            "keywords_zh": rec.get("keywords_zh"),
                            "keywords_en": rec.get("keywords_en"),
                            "tags": rec.get("tags"),
                        }
                    }
                })
        except Exception as e:
            # 避免整批中斷：可在此印警告或記錄 log
            print(f"[load_docs] Skip {p.name}: {e}")

    return items


async def embed_texts(texts: List[str]) -> List[List[float]]:
    url = "https://api.openai.com/v1/embeddings"
    headers = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}
    async with aiohttp.ClientSession() as s:
        payload = {"model": EMBED_MODEL, "input": texts}
        async with s.post(url, headers=headers, json=payload, timeout=120) as r:
            data = await r.json()
            return [d["embedding"] for d in data["data"]]

def save_numpy(vectors: List[List[float]]):
    X = np.array(vectors, dtype="float32")
    # L2 normalize → 之後用內積等於 cosine 相似度
    X /= np.linalg.norm(X, axis=1, keepdims=True) + 1e-12
    np.save(VEC_PATH, X)

async def main():
    print(f"Loading docs from {DOCS_DIR} ...")
    docs = load_docs()
    if not docs:
        print("No docs found. Put PDF/TXT into ./docs then rerun.")
        return
    print(f"Total chunks: {len(docs)}")

    texts = [d.get("text") or d.get("content") or "" for d in docs]
    print("Embedding ...")
    vectors = await embed_texts(texts)

    print("Saving vectors ...")
    save_numpy(vectors)

    print("Saving metadata ...")
    with open(META_PATH, "wb") as f:
        pickle.dump(docs, f)

    print("Done. Index at:", VEC_PATH, " Meta at:", META_PATH)

if __name__ == "__main__":
    asyncio.run(main())
