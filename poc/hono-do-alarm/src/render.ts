import { html, raw } from "hono/html";
import type { ReportContext } from "./types";
import { hourOnly } from "./utils";

function aqiColor(value: number): string {
  if (value <= 50) return "#10b981";
  if (value <= 100) return "#84cc16";
  if (value <= 150) return "#f59e0b";
  if (value <= 200) return "#f97316";
  if (value <= 300) return "#ef4444";
  return "#9333ea";
}

export function renderDetailPage(context: ReportContext): string {
  const now = context.weather.now;
  const air = context.weather.air as { aqi?: number | string; category?: string; primaryPollutant?: { name?: string }; health?: { effect?: string } } | null;
  const aqi = Number(air?.aqi || 0);
  const sun = context.weather.sun as { sunrise?: string; sunset?: string } | null;
  const moon = context.weather.moon as { moonPhase?: Array<{ name?: string }>; name?: string } | null;
  return String(html`<!doctype html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex">
<title>${context.city} 天气详情</title>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/qweather-icons@1.8.0/font/qweather-icons.css">
${raw(`<style>
:root{
  --bg:#eef2f7;
  --card:#ffffff;
  --txt:#1f2937;
  --sub:#6b7280;
  --muted:#9ca3af;
  --acc:#3b82f6;
  --rain:#0ea5e9;
  --warn:#f59e0b;
  --good:#10b981;
  --shadow:0 1px 2px rgba(15,23,42,.04),0 6px 16px rgba(15,23,42,.06);
  --line:#f1f5f9;
}
*{box-sizing:border-box;margin:0;padding:0}
body{background:var(--bg);color:var(--txt);font-family:-apple-system,"PingFang SC","Microsoft YaHei",sans-serif;line-height:1.5;padding:12px;max-width:600px;margin:0 auto;-webkit-font-smoothing:antialiased}
h2{font-size:13px;color:var(--sub);margin:20px 0 10px;font-weight:600;letter-spacing:.5px;padding:0 4px}
.card{background:var(--card);border-radius:18px;padding:16px;box-shadow:var(--shadow)}
.sec-empty{color:var(--muted);padding:6px 0;font-size:14px}
.qi{font-style:normal}
.now{color:#fff;padding:28px 20px 24px;border-radius:18px;box-shadow:0 8px 24px rgba(15,23,42,.15);text-align:center;background-size:cover;background-position:center;min-height:240px;display:flex;flex-direction:column;justify-content:flex-end;position:relative;overflow:hidden;background-image:linear-gradient(rgba(15,23,42,.2),rgba(15,23,42,.65)),url('${context.imageUrl}')}
.now .loc{font-size:14px;opacity:.92;display:flex;align-items:center;justify-content:center;gap:4px}
.now .icon{font-size:72px;margin:6px 0;line-height:1}
.now .temp{font-size:56px;font-weight:700;line-height:1.1}
.now .text{font-size:18px;opacity:.95;margin-top:2px}
.now .meta{font-size:13px;opacity:.88;margin-top:14px;display:flex;justify-content:center;gap:12px;flex-wrap:wrap}
.now .meta span{white-space:nowrap}
.now .loc,.now .icon,.now .temp,.now .text,.now .meta{text-shadow:0 2px 12px rgba(0,0,0,.5)}
.scroll{display:flex;overflow-x:auto;gap:8px;padding-bottom:4px;-webkit-overflow-scrolling:touch}
.scroll::-webkit-scrollbar{display:none}
.h-chip{flex:0 0 72px;background:#f8fafc;border-radius:14px;padding:10px 6px;text-align:center}
.h-chip .t{font-size:11px;color:var(--sub);margin-bottom:6px}
.h-chip .i{font-size:26px;line-height:1;color:var(--acc)}
.h-chip .tmp{font-size:15px;font-weight:600;margin-top:4px;color:var(--txt)}
.h-chip .d{font-size:11px;color:var(--sub);margin-top:2px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.h-chip .p{font-size:11px;color:var(--rain);margin-top:3px;font-weight:600}
.days .day{display:flex;align-items:center;padding:11px 0;border-bottom:1px solid var(--line)}
.days .day:last-child{border-bottom:none}
.days .lab{color:var(--txt);width:60px;font-size:14px;font-weight:500}
.days .ico{font-size:24px;width:36px;text-align:center;color:var(--acc)}
.days .txt{flex:1;padding:0 10px;font-size:14px;color:var(--sub)}
.days .tmp{font-size:14px;font-weight:600;white-space:nowrap}
.days .tmp .lo{color:var(--muted);font-weight:500}
.aq{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap}
.aq .num{font-size:40px;font-weight:700;color:var(--txt);line-height:1}
.aq .pill{display:inline-block;padding:3px 12px;border-radius:999px;font-size:12px;font-weight:600;color:#fff}
.aq .prim{font-size:13px;color:var(--sub);margin-top:10px}
.aq .adv{font-size:13px;color:var(--muted);margin-top:6px;line-height:1.5}
.astro{display:flex;justify-content:space-between;gap:12px;flex-wrap:wrap}
.astro .item{flex:1;min-width:140px;display:flex;align-items:center;gap:10px}
.astro .item .ic{font-size:24px}
.astro .item .lbl{font-size:12px;color:var(--sub)}
.astro .item .val{font-size:14px;font-weight:600;color:var(--txt)}
.warn-row{padding:11px 0;border-bottom:1px solid var(--line)}
.warn-row:last-child{border-bottom:none}
.warn-row .wh{color:var(--warn);font-size:13px;font-weight:600;margin-bottom:5px;display:flex;align-items:center;gap:4px}
.warn-row .we{font-size:14px;font-weight:600;color:var(--txt)}
.warn-chip{background:linear-gradient(135deg,#fbbf24,#f59e0b);color:#fff;border-radius:6px;padding:1px 8px;font-size:11px;font-weight:600;margin-left:6px}
.warn-row .wt{font-size:12px;color:var(--sub);margin-top:3px;line-height:1.5}
.life{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.life .li{background:#f8fafc;border-radius:12px;padding:10px 12px}
.life .li .n{font-size:12px;color:var(--sub)}
.life .li .v{font-size:14px;font-weight:600;color:var(--txt);margin-top:2px}
.foot{text-align:center;color:var(--muted);font-size:12px;padding:18px 0 8px}
</style>`)}</head>
<body>
<div class="now">
  <div class="loc">📍 ${context.city}</div>
  <div class="icon"><i class="qi qi-${now.icon}"></i></div>
  <div class="temp">${now.temp}°</div>
  <div class="text">${now.text} · ${context.holiday.label}</div>
  <div class="meta">
    <span>体感 ${now.feelsLike}°</span>
    <span>湿度 ${now.humidity}%</span>
    <span>${now.windDir}${now.windScale}级</span>
  </div>
</div>
<h2>🚨 气象预警</h2><div class="card">${context.weather.warnings.length ? context.weather.warnings.map((warning) => {
  const item = warning as { title?: string; headLine?: string; eventType?: { name?: string }; level?: string };
  const eventName = item.eventType?.name || "";
  const level = item.level || "";
  return html`<div class="warn-row"><div class="wh">⚠️ ${eventName || "气象预警"}${level ? html`<span class="warn-chip">${level}</span>` : ""}</div>${item.headLine || item.title ? html`<div class="wt">${item.headLine || item.title}</div>` : ""}</div>`;
}) : html`<div class="sec-empty">✅ 暂无气象预警</div>`}</div>
<h2>⏰ 未来 24 小时</h2><div class="card"><div class="scroll">${context.weather.hourly.map((item) => html`<div class="h-chip"><div class="t">${hourOnly(item.fxTime)}</div><div class="i"><i class="qi qi-${item.icon}"></i></div><div class="tmp">${item.temp}°</div><div class="d">${item.text}</div></div>`)}</div></div>
<h2>🗓️ 未来 7 天</h2><div class="card days">${context.weather.daily7.map((item, index) => html`<div class="day"><div class="lab">${index ? item.fxDate : "今天"}</div><div class="ico"><i class="qi qi-${item.iconDay}"></i></div><div class="txt">${item.textDay}</div><div class="tmp">${item.tempMax}° <span class="lo">${item.tempMin}°</span></div></div>`)}</div></div>
<h2>🌫️ 空气质量</h2><div class="card">${air ? html`<div class="aq"><div class="num">${air.aqi}</div>${air.category ? html`<span class="pill" style="background:${aqiColor(aqi)}">${air.category}</span>` : ""}</div>${air.primaryPollutant?.name ? html`<div class="prim">主要污染物 · ${air.primaryPollutant.name}</div>` : ""}${air.health?.effect ? html`<div class="adv">🩺 ${air.health.effect}</div>` : ""}` : html`<div class="sec-empty">🌫️ 暂无空气质量数据</div>`}</div>
<h2>🌅 日出日落 · 月相</h2><div class="card">${sun?.sunrise ? html`<div class="astro"><div class="item"><span class="ic">🌅</span><div><div class="lbl">日出</div><div class="val">${sun.sunrise.slice(11, 16)}</div></div></div>${sun.sunset ? html`<div class="item"><span class="ic">🌇</span><div><div class="lbl">日落</div><div class="val">${sun.sunset.slice(11, 16)}</div></div></div>` : ""}${moon ? html`<div class="item"><span class="ic">🌙</span><div><div class="lbl">月相</div><div class="val">${moon?.moonPhase?.[0]?.name || moon?.name || ""}</div></div></div>` : ""}</div>` : html`<div class="sec-empty">🌌 暂无天文数据</div>`}</div>
<h2>💡 生活提醒</h2><div class="card">${context.weather.indices.length ? html`<div class="life">${context.weather.indices.map((item) => html`<div class="li"><div class="n">${item.name}</div><div class="v">${item.category || item.text || ""}</div></div>`)}</div>` : html`<div class="sec-empty">暂无生活指数数据</div>`}</div>
${context.solarTerm ? html`<h2>🎋 节气</h2><div class="card"><div class="poem">${context.solarTerm.name}</div><div>${context.solarTerm.poem}</div><div>${context.solarTerm.author}《${context.solarTerm.origin}》</div></div>` : context.poetry.content ? html`<h2>📖 画作题诗</h2><div class="card"><div class="poem">${context.poetry.content}</div><div>${context.poetry.author ? html`${context.poetry.author} · ` : ""}${context.poetry.origin}</div></div>` : ""}
<div class="foot">${context.date} 周${context.weekday} · ${context.holiday.label} · ${context.city}</div>
</body></html>`) as string;
}
