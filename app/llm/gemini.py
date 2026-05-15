import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from app.core.config import load_dotenv


_MODEL = None

MODEL_PREFERENCES = (
    "gemini-2.5-flash",
    "gemini-2.0-flash",
    "gemini-1.5-flash-latest",
    "gemini-1.5-flash",
)


def _resolve_model_name(genai) -> str:
    configured = os.environ.get("GEMINI_MODEL")
    if configured:
        return configured

    available = []
    for model in genai.list_models():
        methods = set(getattr(model, "supported_generation_methods", []) or [])
        if "generateContent" in methods:
            name = model.name.removeprefix("models/")
            available.append(name)

    for preferred in MODEL_PREFERENCES:
        if preferred in available:
            return preferred

    if available:
        return available[0]
    raise RuntimeError("No Gemini model with generateContent support is available for this API key")


def gemini(prompt: str, max_tokens: int, temperature: float) -> str:
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    def _call():
        global _MODEL
        import google.generativeai as genai

        if _MODEL is None:
            genai.configure(api_key=api_key)
            _MODEL = genai.GenerativeModel(_resolve_model_name(genai))
        resp = _MODEL.generate_content(
            prompt,
            generation_config=genai.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        return resp.text

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(_call)
        try:
            return future.result(timeout=20)
        except FuturesTimeout as exc:
            raise TimeoutError("Gemini call exceeded 20s") from exc


def parse_json(text: str) -> dict:
    text = text.strip()
    text = re.sub(r"^```(?:json)?\s*", "", text)
    text = re.sub(r"\s*```$", "", text)
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", text, re.DOTALL)
        if match:
            return json.loads(match.group())
        raise
