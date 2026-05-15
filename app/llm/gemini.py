import json
import os
import re
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeout

from app.core.config import load_dotenv


_MODEL = None


def gemini(prompt: str, max_tokens: int, temperature: float) -> str:
    if os.environ.get("SHL_DISABLE_GEMINI") == "1":
        raise RuntimeError("Gemini disabled by SHL_DISABLE_GEMINI")
    load_dotenv()
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("GEMINI_API_KEY is not set")

    def _call():
        global _MODEL
        import google.generativeai as genai

        if _MODEL is None:
            genai.configure(api_key=api_key)
            _MODEL = genai.GenerativeModel("gemini-1.5-flash")
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
