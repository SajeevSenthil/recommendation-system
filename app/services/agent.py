import json
import re

from app.llm.gemini import gemini, parse_json
from app.llm.prompts import INTENT_PROMPT, RESPONSE_PROMPT, SYSTEM_PROMPT
import app.services.guards as guards
from app.services.retriever import retrieve_top_k
from app.services.reranker import rerank


TYPE_LABELS = {
    "K": "knowledge skills test",
    "P": "personality behavior",
    "A": "aptitude cognitive",
    "B": "situational judgment",
    "C": "competency assessment",
    "S": "simulation coding",
    "D": "360 development",
    "E": "assessment center",
}

REFUSAL = {
    "reply": "I can only help with SHL assessment recommendations. Please describe the role you are hiring for.",
    "recommendations": [],
    "end_of_conversation": False,
}

CLARIFICATION = {
    "reply": "Could you tell me what role you are hiring for?",
    "recommendations": [],
    "end_of_conversation": False,
}

def _fmt(messages: list[dict]) -> str:
    lines = []
    for message in messages:
        role = "Recruiter" if message["role"] == "user" else "Agent"
        lines.append(f"{role}: {message['content']}")
    return "\n".join(lines)


def _empty_intent() -> dict:
    return {
        "role": None,
        "seniority": None,
        "domain": None,
        "test_types": [],
        "is_comparison": False,
        "compare_items": [],
        "is_refinement": False,
        "is_off_topic": False,
        "is_vague": False,
        "clarification_already_asked": False,
    }


def _heuristic_intent(messages: list[dict], meta: list[dict]) -> dict:
    intent = _empty_intent()
    history = _fmt(messages).lower()
    last = messages[-1]["content"].lower()
    words = set(re.findall(r"\w+", history))

    off_topic_terms = {
        "salary",
        "compensation",
        "legal",
        "lawsuit",
        "required under",
        "ignore your instructions",
        "forget previous",
        "prompt",
    }
    legal_context = "hipaa" in history and any(term in last for term in ("legally", "required", "satisfy", "law"))
    intent["is_off_topic"] = legal_context or any(term in last for term in off_topic_terms)

    intent["is_comparison"] = any(term in last for term in ("difference between", "compare", "different from", " vs ", " versus "))
    if intent["is_comparison"]:
        intent["compare_items"] = _mentioned_catalog_names(last, meta)

    intent["clarification_already_asked"] = any(
        m["role"] == "assistant" and "?" in m["content"] for m in messages
    )
    intent["is_refinement"] = len(messages) > 1 and any(
        term in last for term in ("add", "drop", "remove", "replace", "actually", "keep", "final", "confirmed", "lock")
    )

    if any(w in words for w in ("graduate", "entry", "junior", "intern")):
        intent["seniority"] = "entry"
    if any(term in history for term in ("mid", "4 year", "3 year", "5 year")):
        intent["seniority"] = "mid"
    if any(w in words for w in ("senior", "principal", "staff")) or "5+" in history:
        intent["seniority"] = "senior"
    if any(w in words for w in ("manager", "director", "head")):
        intent["seniority"] = "manager"
    if any(w in words for w in ("executive", "cxo", "cto", "ceo", "vp", "chief")):
        intent["seniority"] = "executive"

    domains = {
        "tech": {"java", "rust", "spring", "sql", "aws", "docker", "engineer", "developer", "software", "networking"},
        "sales": {"sales", "seller", "selling"},
        "leadership": {"leadership", "executive", "cxo", "director"},
        "clinical": {"healthcare", "hipaa", "medical", "patient"},
        "operations": {"operator", "plant", "manufacturing", "industrial", "contact", "centre", "center", "admin"},
    }
    for domain, domain_words in domains.items():
        if words & domain_words:
            intent["domain"] = domain
            break

    role_patterns = [
        r"hiring\s+(?:a|an|for)?\s*([^.\n?]+)",
        r"screen(?:ing)?\s+([^.\n?]+)",
        r"need\s+(?:an|a)?\s*([^.\n?]+)",
    ]
    for pattern in role_patterns:
        match = re.search(pattern, history)
        if match:
            role = match.group(1).strip(" -")
            role = re.sub(r"^(?:a|an|the)\s+", "", role, flags=re.IGNORECASE)
            if role.lower() not in {"assessment", "assessments", "test", "tests", "solution", "solutions"}:
                intent["role"] = role
            break

    if any(w in words for w in ("java", "python", "sql", "excel", "word", "spring", "aws", "docker", "hipaa", "finance")):
        intent["test_types"].append("K")
    if any(w in words for w in ("simulation", "simulate", "coding", "live")):
        intent["test_types"].append("S")
    if any(w in words for w in ("personality", "opq", "behaviour", "behavior", "fit", "dependability", "safety")):
        intent["test_types"].append("P")
    if any(w in words for w in ("cognitive", "reasoning", "numerical", "aptitude")):
        intent["test_types"].append("A")
    if any(w in words for w in ("situational", "judgement", "judgment", "scenarios")):
        intent["test_types"].append("B")

    vague_terms = {"assessment", "test", "solution", "help", "recommendation"}
    user_token_count = len(re.findall(r"\w+", messages[-1]["content"]))
    intent["is_vague"] = (
        not intent["role"]
        and not intent["domain"]
        and user_token_count <= 10
        and bool(words & vague_terms)
    )
    if "senior leadership" in history and not any(term in history for term in ("cxo", "director-level", "executive", "selection", "developmental")):
        intent["is_vague"] = True
        intent["role"] = None
    return intent


def _extract_intent(messages: list[dict], meta: list[dict]) -> dict:
    heuristic = _heuristic_intent(messages, meta)
    try:
        raw = gemini(INTENT_PROMPT.format(history=_fmt(messages)), max_tokens=300, temperature=0)
        parsed = parse_json(raw)
        if isinstance(parsed, dict):
            merged = {**heuristic, **{k: v for k, v in parsed.items() if v not in (None, [], "")}}
            merged["is_off_topic"] = bool(heuristic["is_off_topic"] or parsed.get("is_off_topic"))
            merged["is_comparison"] = bool(heuristic["is_comparison"] or parsed.get("is_comparison"))
            if not merged.get("compare_items"):
                merged["compare_items"] = heuristic["compare_items"]
            return merged
    except Exception:
        pass
    return heuristic


def build_query(intent: dict, fallback: str) -> str:
    parts = []
    if intent.get("role"):
        parts.append(intent["role"])
    if intent.get("seniority"):
        parts.append(f"{intent['seniority']} level")
    if intent.get("domain"):
        parts.append(intent["domain"])
    for test_type in intent.get("test_types", []):
        if test_type in TYPE_LABELS:
            parts.append(TYPE_LABELS[test_type])
    return " ".join(parts).strip() or fallback


def _mentioned_catalog_names(text: str, meta: list[dict]) -> list[str]:
    lowered = text.lower()
    found = []
    aliases = {
        "opq": "Occupational Personality Questionnaire OPQ32r",
        "opq32r": "Occupational Personality Questionnaire OPQ32r",
        "gsa": "Global Skills Assessment",
        "verify g+": "SHL Verify Interactive G+",
        "dsi": "Dependability and Safety Instrument (DSI)",
        "safety & dependability": "Manufac. & Indust. - Safety & Dependability 8.0",
    }
    for alias, name in aliases.items():
        if alias in lowered:
            found.append(name)
    for item in meta:
        name = item["name"]
        if name.lower() in lowered:
            found.append(name)
    deduped = []
    for name in found:
        if name not in deduped:
            deduped.append(name)
    return deduped


def build_comparison(items: list[str], meta: list[dict], history: str = "") -> dict:
    names = items or _mentioned_catalog_names(history, meta)
    found = []
    for name in names:
        match = next((m for m in meta if name.lower() in m["name"].lower() or m["name"].lower() in name.lower()), None)
        if match and match not in found:
            found.append(match)
    if len(found) < 2:
        return {
            "reply": "I couldn't find both assessments in the catalog to compare.",
            "recommendations": [],
            "end_of_conversation": False,
        }
    parts = []
    for item in found[:3]:
        desc = item.get("description", "")[:220].rstrip()
        types = ", ".join(item.get("keys") or [])
        parts.append(f"{item['name']} ({types}): {desc}.")
    return {
        "reply": "Here is a catalog-grounded comparison: " + " ".join(parts),
        "recommendations": [],
        "end_of_conversation": False,
    }


def _candidate_text(candidates: list[dict]) -> str:
    rows = []
    for item in candidates[:10]:
        rows.append(
            json.dumps(
                {
                    "name": item["name"],
                    "url": item["link"],
                    "test_type": item["test_type"],
                    "description": item.get("description", "")[:180],
                    "keys": item.get("keys", []),
                },
                ensure_ascii=False,
            )
        )
    return "\n".join(rows)


def _recommendation_response(candidates: list[dict], query: str, final: bool) -> dict:
    recommendations = [
        {"name": item["name"], "url": item["link"], "test_type": item["test_type"]}
        for item in candidates[:10]
    ]
    reply = "Here are the SHL assessments I recommend for that hiring need."
    if final:
        reply = "Confirmed. Here is the final SHL assessment shortlist."
    elif "rust" in query.lower():
        reply = "The catalog does not show a Rust-specific test, so this shortlist uses the closest systems, networking, coding, reasoning, and personality signals."
    return {"reply": reply, "recommendations": recommendations, "end_of_conversation": final}


def _is_final_user_message(text: str) -> bool:
    lowered = text.lower()
    phrase_match = any(
        term in lowered
        for term in ("that works", "that's good", "perfect", "covers it", "locking it in", "final list", "final shortlist", "final battery")
    )
    word_match = re.search(r"\b(confirmed|lock|thanks)\b", lowered) is not None
    return phrase_match or word_match


def run_turn(messages: list[dict], index, meta: list[dict]) -> dict:
    turn_count = len(messages)
    history = _fmt(messages)
    final_user = _is_final_user_message(messages[-1]["content"])

    intent = _extract_intent(messages, meta) if turn_count < 7 else _heuristic_intent(messages, meta)

    if intent.get("is_off_topic"):
        return REFUSAL

    if intent.get("is_comparison"):
        return build_comparison(intent.get("compare_items", []), meta, history)

    query = build_query(intent, fallback=history)
    query = f"{history}\n{query}"
    candidates_raw = retrieve_top_k(query, index, meta, k=30)
    candidates = rerank(candidates_raw, query)

    if not intent.get("clarification_already_asked") and turn_count < 6:
        if intent.get("is_vague") and not intent.get("role"):
            return CLARIFICATION
        if intent.get("role") and not intent.get("seniority"):
            return {
                "reply": f"Got it. You are hiring for a {intent['role']}. What is the seniority or experience level you are looking for?",
                "recommendations": [],
                "end_of_conversation": False,
            }

    if not candidates:
        return CLARIFICATION if turn_count < 6 else REFUSAL

    try:
        prompt = SYSTEM_PROMPT + "\n\n" + RESPONSE_PROMPT.format(
            candidates=_candidate_text(candidates),
            history=history,
        )
        raw = gemini(prompt, max_tokens=600, temperature=0.1)
        response = parse_json(raw)
        if final_user:
            response["end_of_conversation"] = True
        return guards.verify(response, candidates)
    except TimeoutError:
        fallback = _recommendation_response(candidates[:3], query, final_user)
        return guards.verify(fallback, candidates)
    except Exception:
        fallback = _recommendation_response(candidates, query, final_user)
        return guards.verify(fallback, candidates)
