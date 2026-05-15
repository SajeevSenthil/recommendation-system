import re


LEADERSHIP_KW = {"lead", "leader", "manag", "director", "executive", "vp", "head", "cxo", "cto", "ceo"}
CODING_KW = {
    "java",
    "python",
    "sql",
    "developer",
    "engineer",
    "code",
    "backend",
    "frontend",
    "software",
    "programming",
    "devops",
    "rust",
    "spring",
    "angular",
    "aws",
    "docker",
}
PERSONALITY_KW = {"personality", "behaviour", "behavior", "culture", "fit", "opq", "motivation", "values"}
COGNITIVE_KW = {"aptitude", "reasoning", "numerical", "verbal", "logic", "abstract", "inductive", "deductive", "cognitive"}

SENIORITY_MAP = {
    "entry": {"Entry-Level", "Graduate"},
    "mid": {"Mid-Professional", "Graduate", "Professional Individual Contributor"},
    "senior": {"Manager", "Front Line Manager", "Supervisor", "Mid-Professional"},
    "manager": {"Manager", "Front Line Manager", "Director"},
    "executive": {"Director", "Executive"},
}


def _signals(query: str) -> dict:
    q = query.lower()
    words = set(re.findall(r"\w+", q))
    seniority = None
    for kw in ("entry", "junior", "graduate", "intern", "final-year"):
        if kw in q:
            seniority = "entry"
            break
    for kw in ("mid", "middle", "4 year", "3 year", "5 year"):
        if kw in q:
            seniority = "mid"
            break
    for kw in ("senior", "lead", "principal", "staff", "5+"):
        if kw in q:
            seniority = "senior"
            break
    for kw in ("manager", "head of", "director"):
        if kw in q:
            seniority = "manager"
            break
    for kw in ("vp", "executive", "cto", "ceo", "chief", "cxo"):
        if kw in q:
            seniority = "executive"
            break
    return {
        "is_leadership": bool(words & LEADERSHIP_KW),
        "is_coding": bool(words & CODING_KW),
        "is_personality": bool(words & PERSONALITY_KW),
        "is_cognitive": bool(words & COGNITIVE_KW),
        "seniority": seniority,
        "keywords": words,
    }


def rerank(candidates: list[dict], query: str) -> list[dict]:
    sig = _signals(query)
    scored = []
    for item in candidates:
        text = (item.get("name", "") + " " + item.get("description", "")).lower()
        text_words = set(re.findall(r"\w+", text))
        keys = item.get("keys", [])
        levels = set(item.get("job_levels", []))

        overlap = len(sig["keywords"] & text_words) / max(len(sig["keywords"]), 1)

        if sig["seniority"] and sig["seniority"] in SENIORITY_MAP:
            wanted = SENIORITY_MAP[sig["seniority"]]
            seniority_score = 1.0 if levels & wanted else 0.2
        else:
            seniority_score = 0.5

        type_score = 0.5
        if sig["is_leadership"] and any(k in keys for k in ["Personality & Behavior", "Competencies"]):
            type_score = 1.0
        elif sig["is_coding"] and any(k in keys for k in ["Knowledge & Skills", "Simulations"]):
            type_score = 1.0
        elif sig["is_cognitive"] and "Ability & Aptitude" in keys:
            type_score = 1.0
        elif sig["is_personality"] and "Personality & Behavior" in keys:
            type_score = 1.0

        final = (
            item.get("semantic_score", 0.0) * 0.65
            + overlap * 0.20
            + seniority_score * 0.10
            + type_score * 0.05
        )
        product = dict(item)
        product["final_score"] = final
        scored.append(product)

    scored.sort(key=lambda x: x["final_score"], reverse=True)
    return scored[:10]
