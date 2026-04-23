from pypdf._page import PageObject


from pypdf import PdfReader

def extract_pdf_pages(pdf_path: str) -> list[tuple[int, str]]:
  reader = PdfReader(pdf_path)
  out: list[tuple[int, str]] = []
  for i, page in enumerate(reader.pages):
    text = page.extract_text() or ""
    out.append((i + 1, text))
  return out