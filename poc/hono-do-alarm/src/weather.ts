import type { AppConfig, WeatherSnapshot } from "./types";

const RAIN_CODES = (code: string) => Number(code) >= 300 && Number(code) < 400;
const SNOW_CODES = (code: string) => Number(code) >= 400 && Number(code) < 500;

export function imageCategory(iconCode: string, text = ""): string {
  const code = Number(iconCode);
  if ([302, 303, 304].includes(code) || text.includes("雷")) return "thunder";
  if (RAIN_CODES(iconCode)) return "rain";
  if (SNOW_CODES(iconCode)) return "snow";
  if (code >= 500 && code <= 515) return "fog";
  if ([101, 102, 103, 104, 151, 152, 153, 154].includes(code) || text.includes("云") || text.includes("阴")) return "cloud";
  return "sun";
}

async function optionalJson(url: string, key: string): Promise<Record<string, unknown> | null> {
  try {
    const response = await fetch(url, { headers: { "X-QW-Api-Key": key }, cf: { cacheTtl: 60 } });
    if (!response.ok) return null;
    const payload = await response.json() as Record<string, unknown>;
    return (!payload.code || payload.code === "200") ? payload : null;
  } catch {
    return null;
  }
}

async function requiredJson(url: string, key: string, name: string): Promise<Record<string, unknown>> {
  const response = await fetch(url, { headers: { "X-QW-Api-Key": key } });
  if (!response.ok) throw new Error(`${name} HTTP ${response.status}`);
  const payload = await response.json() as Record<string, unknown>;
  if (payload.code !== "200") throw new Error(`${name} API code ${payload.code}`);
  return payload;
}

export async function fetchWeather(config: AppConfig, targetDate?: string): Promise<WeatherSnapshot> {
  const base = `https://${config.apiHost}`;
  const loc = config.location;
  const [lon, lat] = config.coords.split(",");
  const date = targetDate || new Date().toISOString().slice(0, 10).replace(/-/g, "");
  const now = await requiredJson(`${base}/v7/weather/now?location=${loc}`, config.apiKey, "now");
  const optional = await Promise.all([
    optionalJson(`${base}/v7/weather/24h?location=${loc}`, config.apiKey),
    optionalJson(`${base}/v7/weather/7d?location=${loc}`, config.apiKey),
    optionalJson(`${base}/weatheralert/v1/current/${lat}/${lon}?lang=zh`, config.apiKey),
    optionalJson(`${base}/v7/indices/1d?location=${loc}&type=1,3,5,6,8,9,10,11,14,15,16`, config.apiKey),
    optionalJson(`${base}/airquality/v1/current/${lat}/${lon}?lang=zh`, config.apiKey),
    optionalJson(`${base}/v7/astronomy/sun?location=${loc}&date=${date}`, config.apiKey),
    optionalJson(`${base}/v7/astronomy/moon?location=${loc}&date=${date}`, config.apiKey)
  ]);
  const airPayload = optional[4] as { indexes?: Array<Record<string, unknown>> } | null;
  const indexes = airPayload?.indexes || [];
  return {
    now: now.now as Record<string, string>,
    hourly: ((optional[0]?.hourly as Array<Record<string, string>>) || []).slice(0, 24),
    daily7: (optional[1]?.daily as Array<Record<string, string>>) || [],
    warnings: (optional[2]?.alerts as Record<string, unknown>[]) || [],
    indices: (optional[3]?.daily as Record<string, string>[]) || [],
    air: indexes.find((item) => item.code === "cn-mee") || indexes[0] || null,
    sun: optional[5],
    moon: optional[6]
  };
}
