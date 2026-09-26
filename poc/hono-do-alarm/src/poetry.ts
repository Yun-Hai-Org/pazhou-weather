import type { Poetry } from "./types";

export async function fetchPoetry(): Promise<Poetry> {
  try {
    const response = await fetch("https://v1.jinrishici.com/all.json");
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const data = await response.json() as Poetry;
    return { content: data.content || "", author: data.author || "佚名", origin: data.origin || "" };
  } catch {
    return { content: "四时俱可喜，最好新秋时。", author: "陆游", origin: "秋思" };
  }
}
