import json
import re
from typing import Any

from app.core.config import DATA_DIR, ROOT_DIR


KEY_CODES = {
    "Knowledge & Skills": "K",
    "Personality & Behavior": "P",
    "Ability & Aptitude": "A",
    "Biodata & Situational Judgment": "B",
    "Competencies": "C",
    "Simulations": "S",
    "Development & 360": "D",
    "Assessment Exercises": "E",
}

CATALOG_DEFAULTS = {
    "entity_id": "",
    "name": "",
    "link": "",
    "scraped_at": "",
    "job_levels": [],
    "job_levels_raw": "",
    "languages": [],
    "languages_raw": "",
    "duration": "",
    "duration_raw": "",
    "status": "",
    "remote": "",
    "adaptive": "",
    "description": "",
    "keys": [],
}

LIST_FIELDS = {"job_levels", "languages", "keys"}
TEXT_FIELDS = set(CATALOG_DEFAULTS) - LIST_FIELDS


CATALOG_PATHS = (
    DATA_DIR / "shl_catalog.json",
    DATA_DIR / "shl_product_catalog.json",
    ROOT_DIR / "shl_catalog.json",
    ROOT_DIR / "shl_product_catalog.json",
)


def _clean_text(value: Any) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text).strip()


def _clean_list(value: Any) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list):
        value = [value]
    return [_clean_text(item) for item in value if _clean_text(item)]


def _load_catalog() -> list[dict]:
    path = next((p for p in CATALOG_PATHS if p.exists()), None)
    if path is None:
        raise FileNotFoundError("Expected shl_catalog.json or shl_product_catalog.json")
    raw = path.read_text(encoding="utf-8")
    data = json.loads(raw, strict=False)
    if not isinstance(data, list):
        raise ValueError("Catalog JSON must be a list of product objects")
    return data


def _normalize_item(item: Any, row_number: int) -> dict:
    if not isinstance(item, dict):
        raise ValueError(f"Catalog item #{row_number} must be an object")

    product = {**CATALOG_DEFAULTS, **item}
    for field in TEXT_FIELDS:
        product[field] = _clean_text(product.get(field))
    for field in LIST_FIELDS:
        product[field] = _clean_list(product.get(field))

    if not product["name"]:
        raise ValueError(f"Catalog item #{row_number} is missing name")
    if not product["link"]:
        raise ValueError(f"Catalog item #{row_number} is missing link")
    if not product["link"].startswith("https://www.shl.com/"):
        raise ValueError(f"Catalog item #{row_number} has a non-SHL link")

    product["test_type"] = _test_type(product)
    return product


def _test_type(item: dict) -> str:
    for key in item.get("keys") or []:
        code = KEY_CODES.get(key)
        if code:
            return code
    return "K"


def _semantic_text(item: dict) -> str:
    keys = item.get("keys") or []
    return _clean_text(
        f"{item.get('name', '')}. {item.get('description', '')} "
        f"Job levels: {item.get('job_levels_raw', '')}. "
        f"Test types: {', '.join(keys)}. "
        f"Duration: {item.get('duration', '')}. "
        f"Remote: {item.get('remote', '')}. Adaptive: {item.get('adaptive', '')}."
    )


def _prepare() -> tuple[list[dict], list[str]]:
    meta = []
    texts = []
    for row_number, item in enumerate(_load_catalog(), start=1):
        product = _normalize_item(item, row_number)
        meta.append(product)
        texts.append(_semantic_text(product))
    return meta, texts


CATALOG_META, CATALOG_TEXTS = _prepare()
CATALOG_LINK_SET = {item["link"] for item in CATALOG_META}
CATALOG_NAME_SET = {item["name"] for item in CATALOG_META}
