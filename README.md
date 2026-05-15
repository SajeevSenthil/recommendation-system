# SHL Assessment Recommender

Stateless FastAPI backend for conversational SHL assessment recommendations.

## Run locally

```bash
pip install -r requirements.txt
python scripts/build_index.py
uvicorn app.main:app --host 0.0.0.0 --port 7860
```

Set `GEMINI_API_KEY` before running with Gemini enabled. If `faiss.index` and
`meta.pkl` are missing under `artifacts/`, or the embedding dependencies are
unavailable, the app falls back to catalog-grounded lexical retrieval so
`/health` and `/chat` still respond.

For local fallback-only smoke tests, set `SHL_DISABLE_GEMINI=1`.

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
