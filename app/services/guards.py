from app.data.catalog import CATALOG_LINK_SET, CATALOG_NAME_SET


def verify(response: dict, candidates: list[dict]) -> dict:
    if not isinstance(response, dict):
        response = {}

    response.setdefault("reply", "")
    response.setdefault("recommendations", [])
    response.setdefault("end_of_conversation", False)

    if not isinstance(response["reply"], str):
        response["reply"] = str(response["reply"])
    if not isinstance(response["recommendations"], list):
        response["recommendations"] = []
    if not isinstance(response["end_of_conversation"], bool):
        response["end_of_conversation"] = False

    clean = []
    for rec in response["recommendations"]:
        if not isinstance(rec, dict):
            continue
        if rec.get("url") not in CATALOG_LINK_SET:
            continue
        if rec.get("name") not in CATALOG_NAME_SET:
            continue
        clean.append(
            {
                "name": rec.get("name", ""),
                "url": rec.get("url", ""),
                "test_type": rec.get("test_type", "K"),
            }
        )
    response["recommendations"] = clean[:10]

    valid = set("KPABCSDE")
    name_map = {c["name"]: c for c in candidates}
    for rec in response["recommendations"]:
        if rec.get("test_type") not in valid:
            meta = name_map.get(rec["name"])
            rec["test_type"] = meta.get("test_type", "K") if meta else "K"

    seen = set()
    deduped = []
    for rec in response["recommendations"]:
        if rec["url"] in seen:
            continue
        seen.add(rec["url"])
        deduped.append(rec)
    response["recommendations"] = deduped

    if response["end_of_conversation"] and not response["recommendations"]:
        response["end_of_conversation"] = False
    if not response["reply"].strip():
        response["reply"] = "Here are my recommendations."

    return response
