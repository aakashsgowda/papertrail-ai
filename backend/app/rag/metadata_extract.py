import re
import json
from .llm import get_client
from ..config import settings

# Matches a line that contains only a section heading name, with an optional
# numeric prefix (e.g. "1.", "2.3", "III.").  Uses MULTILINE so ^ and $ anchor
# to each line.
_SECTION_RE = re.compile(
    r"^[ \t]*(?:(?:[IVXLC]+|[\d]+)(?:\.[\d]+)*\.?\s+)?"
    r"(abstract|introduction|related work|background|preliminaries|"
    r"methodology?|methods?|approach|"
    r"experiments?|experimental setup|evaluation|"
    r"results?|findings|"
    r"discussion|analysis|"
    r"conclusion(?:s)?|summary|"
    r"limitations?|future work|"
    r"acknowledgements?|references?|bibliography)"
    r"[ \t]*$",
    re.IGNORECASE | re.MULTILINE,
)

_METADATA_PROMPT = """
Extract metadata from the first pages of a research paper.
Return ONLY valid JSON with exactly these keys:
- "title": the paper title as a string (empty string if not found)
- "authors": a list of author name strings (empty list if not found)
- "abstract": the abstract text as a string (empty string if not found)

Text:
{text}

JSON:
""".strip()


def extract_paper_metadata(pages: list[tuple[int, str]]) -> dict:
    """
    Returns:
        {
            "paper_title": str,
            "authors": list[str],
            "abstract": str,
            "section_headings": list[str],
        }
    """
    first_pages_text = "\n".join(text for _, text in pages[:2])[:4000]
    llm_data = _extract_with_llm(first_pages_text)

    all_text = "\n".join(text for _, text in pages)
    section_headings = _extract_section_headings(all_text)

    return {
        "paper_title": str(llm_data.get("title", "") or "").strip(),
        "authors": _clean_authors(llm_data.get("authors", [])),
        "abstract": str(llm_data.get("abstract", "") or "").strip(),
        "section_headings": section_headings,
    }


def _extract_with_llm(text: str) -> dict:
    client = get_client()
    resp = client.models.generate_content(
        model=settings.gen_model,
        contents=_METADATA_PROMPT.format(text=text),
    )
    raw = (resp.text if hasattr(resp, "text") and resp.text else "").strip()

    if raw.startswith("```"):
        parts = raw.split("```")
        if len(parts) >= 3:
            raw = parts[1].strip()
    if raw.lower().startswith("json"):
        raw = raw[4:].strip()

    try:
        data = json.loads(raw)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {}


def _clean_authors(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    return [str(a).strip() for a in raw if str(a).strip()]


def _extract_section_headings(text: str) -> list[str]:
    seen: set[str] = set()
    headings: list[str] = []
    for match in _SECTION_RE.finditer(text):
        heading = match.group(0).strip()
        key = heading.lower()
        if key not in seen:
            seen.add(key)
            headings.append(heading)
    return headings


# Maps the bare section name captured by group(1) of _SECTION_RE to a
# canonical label used as the Chunk.section property in Neo4j.
_SECTION_CANONICAL: dict[str, str] = {
    "abstract":           "abstract",
    "introduction":       "introduction",
    "related work":       "background",
    "background":         "background",
    "preliminaries":      "background",
    "methodology":        "method",
    "methods":            "method",
    "method":             "method",
    "approach":           "method",
    "experiments":        "experiments",
    "experimental setup": "experiments",
    "evaluation":         "experiments",
    "results":            "results",
    "findings":           "results",
    "discussion":         "discussion",
    "analysis":           "discussion",
    "conclusion":         "conclusion",
    "conclusions":        "conclusion",
    "summary":            "conclusion",
    "limitations":        "limitations",
    "future work":        "limitations",
    "references":         "references",
    "bibliography":       "references",
    "acknowledgements":   "references",
    "acknowledgement":    "references",
}


def _normalize_section(bare_name: str) -> str:
    """Map a bare section name (group 1 of _SECTION_RE, lowercased) to a canonical label."""
    return _SECTION_CANONICAL.get(bare_name.lower().strip(), "unknown")


def assign_chunk_sections(pages: list[tuple[int, str]], chunk_rows: list[dict]) -> None:
    """
    Assign a canonical 'section' label to each chunk dict in-place.

    Walks pages in document order. When _SECTION_RE detects a heading on a
    page, all subsequent chunks (including those on that page) inherit that
    label.  Chunks before the first heading receive "unknown".
    """
    page_section: dict[int, str] = {}
    current = "unknown"

    for page_no, page_text in pages:
        match = _SECTION_RE.search(page_text)
        if match:
            current = _normalize_section(match.group(1))
        page_section[page_no] = current

    for chunk in chunk_rows:
        chunk["section"] = page_section.get(chunk["page"], "unknown")
