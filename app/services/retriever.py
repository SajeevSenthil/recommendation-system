import os
import pickle
from pathlib import Path

import numpy as np


_BGE_PREFIX = "Represent this sentence for searching relevant passages: "
_MODEL = None


def _get_model():
    global _MODEL
    if _MODEL is None:
        os.environ.setdefault("HF_HUB_OFFLINE", "1")
        from sentence_transformers import SentenceTransformer

        _MODEL = SentenceTransformer("BAAI/bge-small-en-v1.5")
    return _MODEL


def load_index(index_path: str, meta_path: str):
    index_file = Path(index_path)
    meta_file = Path(meta_path)
    if not index_file.exists() or not meta_file.exists():
        raise FileNotFoundError(
            "Missing FAISS artifacts. Run `python scripts/build_index.py` before starting the server."
        )

    import faiss

    index = faiss.read_index(str(index_file))
    with open(meta_file, "rb") as handle:
        meta = pickle.load(handle)
    return index, meta


def warm_embedding_model() -> None:
    _get_model()


def retrieve_top_k(query: str, index, meta: list[dict], k: int = 20) -> list[dict]:
    model = _get_model()
    vec = model.encode([_BGE_PREFIX + query], normalize_embeddings=True)
    vec = np.array(vec, dtype="float32")
    scores, idxs = index.search(vec, k)

    results = []
    for score, idx in zip(scores[0], idxs[0]):
        if idx == -1:
            continue
        item = dict(meta[idx])
        item["semantic_score"] = float(score)
        results.append(item)
    return results
