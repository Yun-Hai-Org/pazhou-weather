import { Hono } from "hono";
import { runAlarm, scheduleNext } from "./alarm";
import type { Env } from "./types";
import { SlotScheduler } from "./do";

export { SlotScheduler };

function pageToken(env: Env): string | null {
  const token = env.PUBLIC_PAGE_TOKEN?.trim();
  return token || null;
}

function authorized(c: { req: { param(key: string): string }; env: Env }): boolean {
  const expected = pageToken(c.env);
  return Boolean(expected) && c.req.param("token") === expected;
}

const app = new Hono<{ Bindings: Env }>();

app.get("/", (c) => c.json({ status: "ok", service: "weather-hono-do-alarm" }));

app.post("/run", async (c) => {
  const body = await c.req.json().catch(() => ({})) as { date?: string; slot?: "am" | "pm" };
  const result = await runAlarm(c.env as unknown as Parameters<typeof runAlarm>[0], body.date, body.slot);
  return c.json(result, result.status === "sent" ? 200 : result.status === "duplicate" ? 200 : 500);
});

app.post("/schedule", async (c) => {
  await scheduleNext(c.env as unknown as Parameters<typeof scheduleNext>[0]);
  return c.json({ status: "scheduled" });
});

app.get("/health", (c) => c.json({ status: "healthy" }));

app.get("/page/:token/detail", async (c) => {
  if (!authorized(c)) return c.text("Not found", 404);
  const html = await (c.env as { ASSETS: { get(key: string): Promise<string | null> } }).ASSETS.get("index.html");
  if (!html) return c.text("Not found", 404);
  return c.html(html);
});

app.get("/page/:token/assets/card/:file", async (c) => {
  if (!authorized(c)) return c.text("Not found", 404);
  const file = c.req.param("file");
  if (!/^[a-z]+\.png$/.test(file)) return c.text("Not found", 404);
  const value = await c.env.ASSETS.get(`assets/card/${file}`, "arrayBuffer");
  if (!value) return c.text("Not found", 404);
  return c.body(value, 200, { "Content-Type": "image/png", "Cache-Control": "public, max-age=86400" });
});

app.get("/page/:token/assets/solar-terms/:file", async (c) => {
  if (!authorized(c)) return c.text("Not found", 404);
  const file = c.req.param("file");
  if (!/^\d+\.jpg$/.test(file)) return c.text("Not found", 404);
  const value = await c.env.ASSETS.get(`assets/solar-terms/${file}`, "arrayBuffer");
  if (!value) return c.text("Not found", 404);
  return c.body(value, 200, { "Content-Type": "image/jpeg", "Cache-Control": "public, max-age=86400" });
});

export default {
  fetch: app.fetch,
  async scheduled(_event: ScheduledController, env: Env, ctx: ExecutionContext): Promise<void> {
    ctx.waitUntil(runAlarm(env as unknown as Parameters<typeof runAlarm>[0]));
    ctx.waitUntil(scheduleNext(env as unknown as Parameters<typeof scheduleNext>[0]));
  }
};
