import type { ReportContext } from "./types";
import { hourOnly } from "./utils";

function truncate(value: string, max = 112): string {
  return value.length <= max ? value : `${value.slice(0, max - 1)}…`;
}

function weatherEmoji(text: string): string {
  if (text.includes("雷")) return "⛈️";
  if (text.includes("雪")) return "❄️";
  if (text.includes("雨")) return "🌧️";
  if (text.includes("雾") || text.includes("霾")) return "🌫️";
  if (text.includes("云") || text.includes("阴")) return "☁️";
  return "☀️";
}

export function buildCard(context: ReportContext): Record<string, unknown> {
  const now = context.weather.now;
  const line1 = `${weatherEmoji(now.text)} ${now.text} ${now.temp}°C | 体感 ${now.feelsLike}°C`;
  const line2 = `💧 湿度 ${now.humidity}% | 🌬️ ${now.windDir} ${now.windScale}级`;
  const items: Array<{ title: string; desc: string }> = [{
    title: "🌡️ 天气实况",
    desc: truncate(`${line1}\n${line2}`)
  }];
  const hourly = context.weather.hourly.slice(0, 3).map((item) => {
    return `🕐${hourOnly(item.fxTime)} ${weatherEmoji(item.text)}${item.text} ${item.temp}°C`;
  }).join("\n");
  if (hourly) items.push({ title: "⏭️ 未来3小时", desc: hourly });
  if (context.poetry.content) {
    items.push({
      title: context.solarTerm ? "🎋 节气诗句" : "📖 画作题诗",
      desc: truncate(`${context.poetry.content}${context.poetry.author ? ` —— ${context.poetry.author}` : ""}${context.poetry.origin ? `《${context.poetry.origin}》` : ""}`)
    });
  }
  return {
    card_type: "news_notice",
    source: { icon_url: "https://openweathermap.org/img/wn/03d@2x.png", desc: "天气预报", desc_color: 0 },
    main_title: { title: truncate(`🌤️ ${context.city}`, 26), desc: truncate(`📅 ${context.date} 周${context.weekday} ${context.time} · ${context.holiday.label}`, 30) },
    card_image: { url: context.imageUrl, aspect_ratio: 1.78 },
    vertical_content_list: items,
    card_action: { type: 1, url: context.jumpUrl }
  };
}

export async function sendCards(webhooks: string[], card: Record<string, unknown>): Promise<void> {
  const errors: string[] = [];
  await Promise.all(webhooks.map(async (webhook, index) => {
    const response = await fetch(webhook, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ msgtype: "template_card", template_card: card })
    });
    const payload = await response.json().catch(() => ({})) as { errcode?: number; errmsg?: string };
    if (!response.ok || payload.errcode !== 0) errors.push(`#${index + 1} ${response.status} ${payload.errmsg || ""}`);
  }));
  if (errors.length) throw new Error(`WeCom delivery failed: ${errors.join("; ")}`);
}
