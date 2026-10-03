import type { Slot } from "./types";

export interface ClevelandArtwork {
  imageUrl: string;
  title: string;
  culture: string;
  created: string;
  poem?: string;
}

interface ClevelandApiResponse {
  data?: Array<{
    id?: number;
    title?: string;
    culture?: string[];
    creation_date?: string;
    images?: { web?: { url?: string } };
    inscriptions?: Array<{ inscription?: string }>;
  }>;
}

const CLEVELAND_PAGE_SIZE = 50;
const CLEVELAND_PAGES = [0, 50, 100] as const;

function coverImage1024x576(imageUrl: string): string {
  const cropper = new URL("https://wsrv.nl/");
  cropper.searchParams.set("url", imageUrl);
  cropper.searchParams.set("w", "1024");
  cropper.searchParams.set("h", "576");
  cropper.searchParams.set("fit", "cover");
  cropper.searchParams.set("output", "jpg");
  return cropper.toString();
}

export async function fetchDailyChinesePainting(date: string, slot?: Slot): Promise<ClevelandArtwork | null> {
  try {
    const dayIndex = Math.floor(Date.parse(`${date}T00:00:00Z`) / 86_400_000);
    const dayOffset = dayIndex * 2 + (slot === "pm" ? 1 : 0);

    const pageResponses = await Promise.all(CLEVELAND_PAGES.map(async (skip) => {
      const url = `https://openaccess-api.clevelandart.org/api/artworks/?q=chinese%20landscape&has_image=1&cc0=1&type=Painting&limit=${CLEVELAND_PAGE_SIZE}&skip=${skip}`;
      const response = await fetch(url, { cf: { cacheTtl: 86_400 } });
      if (!response.ok) throw new Error(`Cleveland API ${skip}: ${response.status}`);
      return await response.json() as ClevelandApiResponse;
    }));
    const seenIds = new Set<number>();
    const pool = pageResponses.flatMap((payload) => (payload.data || []).filter((item) => {
      const isValid = item.images?.web?.url
        && item.id !== undefined
        && item.culture?.some((entry) => entry.includes("China"))
        && !seenIds.has(item.id);
      if (isValid && item.id !== undefined) seenIds.add(item.id);
      return isValid;
    }));
    if (pool.length === 0) return null;
    const item = pool[((dayOffset % pool.length) + pool.length) % pool.length];
    if (!item?.images?.web?.url) return null;
    let poem = "";
    for (const insc of (item.inscriptions || [])) {
      if (!insc.inscription) continue;
      const lines = insc.inscription.split("\n").map((line) => line.trim()).filter((line) => {
        return /^[\u4e00-\u9fff，。、！？\s]+$/.test(line) && line.length >= 4 && line.length <= 20;
      }).filter((line) => !/爲畫作題跋印於書並山人$/.test(line) && !/^[康乾雍嘉道光緒宣統]/.test(line) && !line.includes("先生") && !line.includes("道盟"));
      if (lines.length >= 2 && lines.length <= 8) {
        poem = lines.join("\n");
        break;
      }
    }
    return {
      imageUrl: coverImage1024x576(item.images.web.url),
      title: item.title || "中国传统山水画",
      culture: item.culture?.join(", ") || "中国",
      created: item.creation_date || "",
      poem: poem || undefined
    };
  } catch {
    return null;
  }
}
