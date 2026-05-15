import math
import pickle
import re
from collections import Counter
from pathlib import Path

import numpy as np

from app.data.catalog import CATALOG_META, CATALOG_TEXTS


_BGE_PREFIX = "Represent this sentence for searching relevant passages: "
_MODEL = None


def _tokens(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9+#.]+", text.lower()) if len(t) > 1]


def _get_model():
    global _MODEL
    if _MODEL is None:
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer("BAAI/bge-small-en-v1.5")
    return _MODEL


def load_index(index_path: str = "artifacts/faiss.index", meta_path: str = "artifacts/meta.pkl"):
    if Path(index_path).exists() and Path(meta_path).exists():
        try:
            import faiss

            index = faiss.read_index(index_path)
            with open(meta_path, "rb") as handle:
                meta = pickle.load(handle)
            return index, meta
        except Exception as exc:
            print(f"Falling back to lexical retrieval: {exc}")
    return None, CATALOG_META


def _lexical_retrieve(query: str, meta: list[dict], k: int) -> list[dict]:
    query_tokens = Counter(_tokens(query))
    results = []
    for item, text in zip(meta, CATALOG_TEXTS):
        doc_tokens = Counter(_tokens(text))
        overlap = sum(min(count, doc_tokens[token]) for token, count in query_tokens.items())
        phrase_bonus = 0
        haystack = text.lower()
        for token in query_tokens:
            if token in haystack:
                phrase_bonus += 0.15
        score = overlap / math.sqrt(max(sum(doc_tokens.values()), 1)) + phrase_bonus
        if score > 0:
            product = dict(item)
            product["semantic_score"] = float(score)
            results.append(product)
    results.sort(key=lambda item: item["semantic_score"], reverse=True)
    return results[:k]


def retrieve_top_k(query: str, index, meta: list[dict], k: int = 20) -> list[dict]:
    if index is None:
        return _lexical_retrieve(query, meta, k)

    try:
        model = _get_model()
        vec = model.encode([_BGE_PREFIX + query], normalize_embeddings=True)
        vec = np.array(vec, dtype="float32")
        scores, idxs = index.search(vec, k)
    except Exception as exc:
        print(f"Semantic retrieval failed, using lexical fallback: {exc}")
        return _lexical_retrieve(query, meta, k)

    results = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx == -1:
            continue
        item = dict(meta[idx])
        item["semantic_score"] = float(score)
        results.append(item)
    return results
