import { getOrCreateUserId } from "./user";

type AskResponse = {
  answer: string;
  citations: Array<{ doc_id: string; page?: number | null; chunk_id: string; score?: number | null }>;
  context: Array<{ doc_id: string; page?: number | null; chunk_id: string; score?: number | null; text: string }>;
};

export async function uploadPdf(file: File): Promise<{ doc_id: string }> {
  const userId = await getOrCreateUserId();

  const base = process.env.NEXT_PUBLIC_API_BASE;
  if (!base) throw new Error("NEXT_PUBLIC_API_BASE is not set");

  const form = new FormData();
  form.append("file", file);

  const res = await fetch(`${base}/upload`, {
    method: "POST",
    headers: { "X-User-Id": userId },
    body: form,
  });

  if (!res.ok) throw new Error(await res.text());
  return res.json();
}

export async function askQuestion(question: string): Promise<AskResponse> {
  const userId = await getOrCreateUserId();

  const base = process.env.NEXT_PUBLIC_API_BASE;
  if (!base) throw new Error("NEXT_PUBLIC_API_BASE is not set");

  const form = new FormData();
  form.append("question", question);

  const res = await fetch(`${base}/ask`, {
    method: "POST",
    headers: { "X-User-Id": userId },
    body: form,
  });

  if (!res.ok) throw new Error(await res.text());
  return res.json();
}