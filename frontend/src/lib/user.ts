export async function getOrCreateUserId(): Promise<string> {
  if (typeof window === "undefined") return "server";

  let id = localStorage.getItem("user_id");
  if (id) return id;

  const base = process.env.NEXT_PUBLIC_API_BASE;
  if (!base) throw new Error("NEXT_PUBLIC_API_BASE is not set");

  const res = await fetch(`${base}/session`, { method: "POST" });
  if (!res.ok) throw new Error(`Failed to create session: ${await res.text()}`);

  const data = (await res.json()) as { user_id: string };
  id = data.user_id;
  localStorage.setItem("user_id", id);
  return id;
}
