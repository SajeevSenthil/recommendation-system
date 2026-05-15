import os
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = ROOT_DIR / "data"
ARTIFACTS_DIR = ROOT_DIR / "artifacts"
SCRIPTS_DIR = ROOT_DIR / "scripts"

INDEX_PATH = ARTIFACTS_DIR / "faiss.index"
META_PATH = ARTIFACTS_DIR / "meta.pkl"

_ENV_LOADED = False


def load_dotenv() -> None:
    global _ENV_LOADED
    if _ENV_LOADED:
        return
    _ENV_LOADED = True

    env_path = ROOT_DIR / ".env"
    if not env_path.exists():
        return

    with open(env_path, encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
