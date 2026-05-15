# SHL Assessment Recommender API

A conversational, stateless FastAPI backend for an SHL assessment recommender. This agent clarifies recruiting intents, enforces strict recommendation constraints, and retrieves tests from a local FAISS index built on the official SHL catalog.

## Local Setup & Running

1. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

2. **Set Environment Variables**
   Ensure you have a `.env` file at the root with your Gemini API key:
   ```env
   GEMINI_API_KEY=your_gemini_api_key_here
   ```

3. **Build the Search Index**
   Before running the server for the first time, you must build the FAISS index:
   ```bash
   python scripts/build_index.py
   ```
   *(This will create `faiss.index` and `meta.pkl` in the `artifacts/` folder).*

4. **Start the API Server**
   ```bash
   export USE_TF=0  # Use if you run into tensorflow import errors
   uvicorn app.main:app --host 0.0.0.0 --port 7860 --reload
   ```

5. **Test via Swagger UI**
   Open your browser and navigate to: [http://localhost:7860/docs](http://localhost:7860/docs)

---

## Testing The Endpoints (Example Conversations)

Because the API is stateless, you must pass the full conversation history back to the `/chat` endpoint on every turn.

### Example 1: Vague Request (Forces Clarification)
**POST** to `http://localhost:7860/chat`
```json
{
  "messages": [
    {"role": "user", "content": "I need a solution for senior leadership."}
  ]
}
```

### Example 2: Providing Context (Forces Recommendation)
Append the agent's reply and your new answer:
**POST** to `http://localhost:7860/chat`
```json
{
  "messages": [
    {"role": "user", "content": "I need a solution for senior leadership."},
    {"role": "assistant", "content": "Could you tell me what role you are hiring for?"},
    {"role": "user", "content": "The pool consists of CXOs and directors."}
  ]
}
```

### Example 3: Comparison Request
**POST** to `http://localhost:7860/chat`
```json
{
  "messages": [
    {"role": "user", "content": "What is the difference between the OPQ32r and the Global Skills Assessment?"}
  ]
}
```

---

## Deployment to Hugging Face Spaces

This project is perfectly formatted to be deployed as a **Docker Space** on Hugging Face.

1. Create a new Space on [Hugging Face](https://huggingface.co/spaces).
2. Choose **Docker** as the Space SDK (Blank template).
3. Connect your Git repository or push this repository directly to the Hugging Face remote using `git push`.
4. Add your Gemini API Key:
   - Go to your Space's **Settings**.
   - Find **Variables and secrets**.
   - Add a New Secret:
     - **Name:** `GEMINI_API_KEY`
     - **Value:** `<your-actual-api-key>`
5. The platform will automatically detect the `Dockerfile`, build the image, and start the `uvicorn` server on port 7860.
