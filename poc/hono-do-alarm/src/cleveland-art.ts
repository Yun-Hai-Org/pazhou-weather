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

const CLEVELAND_TOTAL = 120;

export async function fetchDailyChinesePainting(date: string): Promise<ClevelandArtwork | null> {
  try {
    const dayIndex = Math.floor(Date.parse(`${date}T00:00:00Z`) / 86_400_000);
    const offset = ((dayIndex % CLEVELAND_TOTAL) + CLEVELAND_TOTAL) % CLEVELAND_TOTAL;
    const page = Math.floor(offset / 50) + 1;
    const skip = (page - 1) * 50;
    const url = `https://openaccess-api.clevelandart.org/api/artworks/?q=chinese%20landscape&has_image=1&cc0=1&type=Painting&limit=50&skip=${skip}`;
    const response = await fetch(url, { cf: { cacheTtl: 86_400 } });
    if (!response.ok) return null;
    const payload = await response.json() as ClevelandApiResponse;
    const items = (payload.data || []).filter((item) =>
      item.images?.web?.url && item.culture?.some((entry) => entry.includes("China"))
    );
    const item = items[offset % 50];
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
      imageUrl: item.images.web.url,
      title: item.title || "中国传统山水画",
      culture: item.culture?.join(", ") || "中国",
      created: item.creation_date || "",
      poem: poem || undefined
    };
  } catch {
    return null;
  }
}
