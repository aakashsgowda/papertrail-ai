import json
from .llm import get_client
from ..config import settings

_VALID_TYPES = frozenset({
    "MLModel", "Dataset", "Metric", "Task",
    "Method", "Framework", "Benchmark", "Finding", "Other",
})

_MAX_NAME_LEN = 120

ENTITY_PROMPT = """
You are an information-extraction assistant for machine learning and NLP research papers.

Extract the most important entities from the text below.
Return ONLY valid JSON — a list of objects, each with exactly two keys: "name" and "type".

Entity types (use ONLY these):
- MLModel    : a named model or architecture (e.g. GPT-4, BERT, ResNet-50, LLaMA 2)
- Dataset    : a named dataset or corpus (e.g. ImageNet, SQuAD, COCO, GLUE)
- Metric     : an evaluation metric or score (e.g. F1, BLEU, perplexity, top-1 accuracy)
- Task       : an NLP/ML task (e.g. text classification, machine translation, object detection)
- Method     : a technique, algorithm, or training procedure (e.g. attention, LoRA, RLHF, dropout)
- Framework  : a software framework or library (e.g. PyTorch, TensorFlow, JAX, HuggingFace)
- Benchmark  : a named evaluation benchmark or leaderboard (e.g. SuperGLUE, BIG-bench, HELM)
- Finding    : a short key claim or result (max 15 words, e.g. "outperforms GPT-3 by 4.1 BLEU points")
- Other      : only if none of the above apply

Rules:
- Return at most 8 entities.
- Use the most specific type available; avoid Other when a better type fits.
- Names must be concise — for Finding, summarise the claim in at most 15 words.
- Do not return duplicate names.
- If no entities are found, return an empty list [].

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

    # Strip ```json ... ``` fences
    if raw.startswith("```"):
        parts = raw.split("```")
        if len(parts) >= 3:
            raw = parts[1].strip()
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()

    try:
        data = json.loads(raw)
        if isinstance(data, list):
            return _clean(data)
    except Exception:
        pass
    return []


def _clean(data: list) -> list[dict]:
    seen: set[str] = set()
    out: list[dict] = []

    for item in data:
        if not isinstance(item, dict):
            continue

        name = str(item.get("name", "")).strip()
        if not name:
            continue

        # Enforce max length — truncate rather than drop
        if len(name) > _MAX_NAME_LEN:
            name = name[:_MAX_NAME_LEN - 1] + "…"

        # Deduplicate by normalised name
        key = name.lower()
        if key in seen:
            continue
        seen.add(key)

        # Enforce type allowlist — unknown types fall back to Other
        etype = str(item.get("type", "Other")).strip()
        if etype not in _VALID_TYPES:
            etype = "Other"

        out.append({"name": name, "type": etype})
        if len(out) == 8:
            break

    return out
