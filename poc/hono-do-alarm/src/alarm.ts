import { configFromEnv } from "./config";
import { buildCard, sendCards } from "./wecom";
import { uploadToPages } from "./pages-upload";
import { renderDetailPage } from "./render";
import { resolveHoliday } from "./holiday";
import { solarTermFor } from "./solar-terms";
import { fetchDailyChinesePainting } from "./cleveland-art";
import { businessSlot, nextAlarmIso } from "./time";
import { fetchWeather, imageCategory } from "./weather";
import type { Slot } from "./types";

export interface AlarmEnv extends Record<string, unknown> {
  SLOT_DO: DurableObjectNamespace;
}

const PAGE_URLS: Record<string, string> = {
  sun: "assets/solar-terms/7.jpg",
  cloud: "assets/solar-terms/16.jpg",
  rain: "assets/solar-terms/2.jpg",
  snow: "assets/solar-terms/20.jpg",
  thunder: "assets/solar-terms/10.jpg",
  fog: "assets/solar-terms/15.jpg"
};

export async function runAlarm(env: AlarmEnv, date?: string, slot?: Slot): Promise<{ status: string; slot: string; pagesDeploymentId?: string }> {
  const business = businessSlot();
  const forceHourly = String(env.FORCE_HOURLY_RUN || "") === "1";
  const requestId = crypto.randomUUID();
  const target = { date: date || business.date, slot: slot || business.slot };
  const slotKey = `${target.date}:${target.slot}`;
  const scheduler = env.SLOT_DO.get(env.SLOT_DO.idFromName("weather-slot"));
  const claim = await scheduler.fetch("https://do/claim", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...target, requestId })
  });
  let claimResult: { status: string } = { status: "claimed" };
  try { claimResult = await claim.json() as { status: string }; } catch { /* empty body */ }
  if (claimResult.status !== "claimed" && !(forceHourly && !date && !slot)) {
    return { status: "duplicate", slot: slotKey };
  }
  const config = configFromEnv(env as Record<string, string | undefined>);
  const webhooks = config.prodWebhooks;
  try {
    const weather = await fetchWeather(config, target.date.replace(/-/g, ""));
    const holiday = await resolveHoliday(target.date);
    const term = solarTermFor(target.date);
    const cleveland = await fetchDailyChinesePainting(target.date);
    const poetry = term ? { content: term.poem, author: term.author, origin: term.origin }
      : cleveland?.poem ? { content: cleveland.poem, author: "", origin: cleveland.title }
      : { content: "", author: "", origin: "" };
    const category = imageCategory(weather.now.icon, weather.now.text);
    const base = config.pagesBaseUrl.replace(/\/$/, "");
    const pageToken = String(env.PUBLIC_PAGE_TOKEN || "").trim();
    if (!pageToken) throw new Error("Missing PUBLIC_PAGE_TOKEN");
    const context = {
      slot: target.slot,
      requestId,
      date: target.date,
      time: business.time,
      weekday: business.weekday,
      holiday,
      city: config.cityName,
      weather,
      solarTerm: term,
      poetry,
      imageUrl: term ? `${base}/${term.imageUrl}` : cleveland?.imageUrl || `${base}/${PAGE_URLS[category]}`,
      jumpUrl: `${base}/page/${pageToken}/detail`
    };
    const card = buildCard(context);
    if (!config.skipSend) await sendCards(webhooks, card);
    let pagesDeploymentId: string | undefined;
    try {
      const html = renderDetailPage(context);
      pagesDeploymentId = await uploadToPages(env.ASSETS as import("./types").KVNamespace, html);
    } catch (error) {
      pagesDeploymentId = undefined;
      console.warn(JSON.stringify({ requestId, slot: slotKey, stage: "pages", error: String(error) }));
      await scheduler.fetch("https://do/notify", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ webhooks, stage: "pages-upload", slot: slotKey, requestId, error: String(error) })
      });
    }
    if (!forceHourly || date || slot) await scheduler.fetch("https://do/sent", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ ...target, pagesDeploymentId })
    });
    return { status: "sent", slot: slotKey, pagesDeploymentId };
  } catch (error) {
    await scheduler.fetch("https://do/notify", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ webhooks, stage: "report", slot: slotKey, requestId, error: String(error) })
    });
    if (!forceHourly || date || slot) await scheduler.fetch("https://do/release", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(target)
    });
    throw error;
  }
}

export function scheduleNext(env: AlarmEnv): Promise<void> {
  const scheduler = env.SLOT_DO.get(env.SLOT_DO.idFromName("weather-slot"));
  return scheduler.fetch("https://do/schedule", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ nextEpochMs: nextAlarmIso() })
  }).then(() => undefined);
}
