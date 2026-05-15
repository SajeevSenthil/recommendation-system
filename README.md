# SHL Assessment Recommender

Stateless FastAPI backend for conversational SHL assessment recommendations.

## Run locally

```bash
pip install -r requirements.txt
python scripts/build_index.py
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

Set `GEMINI_API_KEY` in `.env` or your deployment environment before starting.
Optionally set `GEMINI_MODEL`; if omitted, the app chooses an available Gemini
model that supports `generateContent`.
The server requires `artifacts/faiss.index`, `artifacts/meta.pkl`, and the BGE
embedding model. Build the index once with `python scripts/build_index.py`, then
deploy those artifacts with the app.

There is no keyword-search fallback in the runtime path. Retrieval is FAISS +
BGE embeddings, followed by metadata reranking.
At runtime the BGE model is loaded offline from the local Hugging Face cache; if
it is not cached, startup fails fast instead of hanging on model download.

## Layout

```text
app/
  api/       FastAPI routes
  core/      paths and local env loading
  data/      catalog loader
  llm/       Gemini wrapper and prompts
  schemas/   Pydantic request/response models
  services/  agent, retrieval, reranking, guards
data/        SHL product catalog JSON
docs/        assignment notes and sample conversations
scripts/     one-off utility scripts
artifacts/   generated FAISS index files
```

## Endpoints

- `GET /health` returns `{"status": "ok"}`
- `POST /chat` accepts stateless `messages` and returns `reply`,
  `recommendations`, and `end_of_conversation`
