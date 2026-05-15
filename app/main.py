import os
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import router
from app.core.config import INDEX_PATH, META_PATH
from app.core.config import load_dotenv
from app.services.retriever import load_index, warm_embedding_model


@asynccontextmanager
async def lifespan(app: FastAPI):
    load_dotenv()
    if not os.environ.get("GEMINI_API_KEY"):
        raise RuntimeError("GEMINI_API_KEY is required. Add it to .env or the deployment environment.")
    app.state.index, app.state.meta = load_index(str(INDEX_PATH), str(META_PATH))
    warm_embedding_model()
    print("Startup complete. Semantic FAISS retrieval is ready.")
    yield


app = FastAPI(lifespan=lifespan)
app.include_router(router)
