import { DurableObject } from "cloudflare:workers";
import { scheduleNext, runAlarm } from "./alarm";
import { SlotStore } from "./idempotency";
import { notifyFailure } from "./notify";

export interface DoEnv extends Record<string, unknown> {
  SLOT_DO: DurableObjectNamespace;
}

export class SlotScheduler extends DurableObject<DoEnv> {
  private store = new SlotStore(this.ctx.storage);

  async fetch(request: Request): Promise<Response> {
    const url = new URL(request.url);
    let body: Record<string, string> = {};
    try { body = await request.json() as Record<string, string>; } catch { /* empty body */ }
    const date = String(body.date || "");
    const slot = String(body.slot || "");
    if (url.pathname === "/claim") {
      const claimed = await this.store.claim(date, slot, String(body.requestId || crypto.randomUUID()));
      return Response.json({ status: claimed ? "claimed" : "duplicate" });
    }
    if (url.pathname === "/sent") {
      await this.store.markSent(date, slot, body.pagesDeploymentId);
      return Response.json({ status: "sent" });
    }
    if (url.pathname === "/release") {
      await this.store.release(date, slot);
      return Response.json({ status: "released" });
    }
    if (url.pathname === "/notify") {
      let devUrls: string[] = [];
      try { devUrls = JSON.parse(String(body.dev || "[]")) as string[]; } catch { /* invalid dev json */ }
      await notifyFailure(devUrls, body.stage || "unknown", `${date}:${slot}`, body.requestId || "", body.error || "unknown");
      return Response.json({ status: "notified" });
    }
    if (url.pathname === "/schedule") {
      await this.ctx.storage.setAlarm(Number(body.nextEpochMs));
      return Response.json({ status: "scheduled" });
    }
    return new Response("Not found", { status: 404 });
  }

  async alarm(): Promise<void> {
    try {
      await runAlarm(this.env as never, undefined, undefined);
    } catch (error) {
      console.error(JSON.stringify({ stage: "alarm", error: String(error) }));
    } finally {
      await scheduleNext(this.env);
    }
  }
}
