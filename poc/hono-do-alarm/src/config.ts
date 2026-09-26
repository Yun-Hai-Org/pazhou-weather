import type { AppConfig } from "./types";

function splitUrls(value: string | undefined): string[] {
  return [...new Set((value || "").split(/[,;\n]+/).map((item) => item.trim()).filter(Boolean))];
}

export function configFromEnv(env: Record<string, string | undefined>): AppConfig {
  const apiKey = env.QWEATHER_API_KEY?.trim();
  if (!apiKey) throw new Error("Missing QWEATHER_API_KEY");
  const prod = splitUrls(env.WECOM_WEBHOOK_URL_PROD);
  const dev = splitUrls(env.WECOM_WEBHOOK_URL_DEV);
  if ((env.APP_ENV || "dev") === "prod" && prod.length === 0) throw new Error("Missing WECOM_WEBHOOK_URL_PROD");
  return {
    appEnv: env.APP_ENV || "dev",
    apiKey,
    apiHost: env.QWEATHER_API_HOST?.trim() || "devapi.qweather.com",
    cityName: env.CITY_NAME?.trim() || "广州·海珠琶洲",
    location: env.CITY_LOCATION?.trim() || "101280108",
    coords: env.CITY_COORDS?.trim() || "113.384,23.101",
    prodWebhooks: prod,
    devWebhooks: dev,
    pagesBaseUrl: env.PUBLIC_BASE_URL?.trim() || env.PAGES_BASE_URL?.trim() || "",
    pagesProject: env.CF_PAGES_PROJECT?.trim() || "",
    accountId: env.CLOUDFLARE_ACCOUNT_ID?.trim() || "",
    apiToken: env.CLOUDFLARE_API_TOKEN?.trim() || "",
    skipSend: env.WECOM_SKIP_SEND?.trim() === "1"
  };
}
