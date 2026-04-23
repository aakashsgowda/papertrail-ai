def chunk_text(text: str, chunk_size: int, overlap: int) -> list[str]:

  t = (text or "").strip()
  if not t:
    return []
  
  if chunk_size <= 0:
    return []
  overlap = max(0, min(overlap, chunk_size - 1))
  
  chunks: list[str] = []
  start = 0
  n=len(t)

  while start < n:
    end = min(start + chunk_size, n)
    piece = t[start:end].strip()
    if piece:
      chunks.append(piece)
    if end == n:
      break
    start = end - overlap
  return chunks
