import json
from .llm import get_client
from ..config import settings

ENTITY_PROMPT = """
Extract important entities from the text.
Return ONLY valid JSON as a list of objects with keys: name, type.
Entity type must be one of: Person, Organization, Location, Product, Concept, Metric, Law, Date, Other.
Limit to at most 8 entities. Use short names.

Text:
{chunk}

JSON:
""".strip()

def extract_entities_from_chunk(chunk: str) -> list[dict]:
    client = get_client()
    resp = client.models.generate_content(
        model=settings.gen_model,
        contents=ENTITY_PROMPT.format(chunk=chunk[:6000]),
    )

    raw = resp.text.strip() if hasattr(resp, "text") and resp.text else ""

    # Strip ```json ... ``` wrappers
    if raw.startswith("```"):
        parts = raw.split("```")
        if len(parts) >= 3:
            raw = parts[1].strip()

    # Sometimes it starts with "json" after stripping fences
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()

    try:
        data = json.loads(raw)
        if isinstance(data, list):
            cleaned = []
            for x in data:
                if not isinstance(x, dict):
                    continue
                name = str(x.get("name", "")).strip()
                etype = str(x.get("type", "Other")).strip()
                if name:
                    cleaned.append({"name": name, "type": etype or "Other"})
            return cleaned[:8]
    except Exception:
        return []
    return []