from pydantic import BaseModel

class PaperMetadata(BaseModel):
  paper_title: str
  authors: list[str]
  abstract: str
  section_headings: list[str]

class UploadResponse(BaseModel):
  doc_id: str
  metadata: PaperMetadata