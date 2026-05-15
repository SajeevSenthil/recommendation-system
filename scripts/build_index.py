import pickle
import sys
from pathlib import Path

import numpy as np

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from app.data.catalog import CATALOG_META, CATALOG_TEXTS


def main() -> None:
    from sentence_transformers import SentenceTransformer
    import faiss

    model = SentenceTransformer("BAAI/bge-small-en-v1.5")
    vectors = model.encode(
        CATALOG_TEXTS,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    vectors = np.array(vectors, dtype="float32")

    index = faiss.IndexFlatIP(vectors.shape[1])
    index.add(vectors)

    artifacts_dir = ROOT_DIR / "artifacts"
    artifacts_dir.mkdir(exist_ok=True)

    faiss.write_index(index, str(artifacts_dir / "faiss.index"))
    with open(artifacts_dir / "meta.pkl", "wb") as handle:
        pickle.dump(CATALOG_META, handle)

    print(f"Index built: {index.ntotal} items, dim={vectors.shape[1]}")


if __name__ == "__main__":
    main()
