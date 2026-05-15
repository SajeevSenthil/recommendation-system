import subprocess
import sys
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import INDEX_PATH, META_PATH, ROOT_DIR, SCRIPTS_DIR
from app.services.retriever import load_index


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not (INDEX_PATH.exists() and META_PATH.exists()):
        print("Index not found; attempting to build now...")
        try:
            subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "build_index.py")],
                check=True,
                timeout=120,
                capture_output=True,
                text=True,
                cwd=str(ROOT_DIR),
            )
        except Exception as exc:
            print(f"Index build skipped; lexical retrieval fallback will be used: {exc}")
    app.state.index, app.state.meta = load_index(str(INDEX_PATH), str(META_PATH))
    print("Startup complete.")
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)
