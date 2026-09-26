import type { KVNamespace } from "./types";

export async function uploadToPages(kv: KVNamespace, html: string): Promise<string> {
  await kv.put("index.html", html);
  return `kv:${Date.now()}`;
}
