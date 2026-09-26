import { maskWebhook } from "./utils";

export async function notifyDev(webhooks: string[], stage: string, slot: string, requestId: string, error: unknown): Promise<void> {
  const message = `${stage} failed for ${slot}\nrequestId=${requestId}\n${String(error).slice(0, 900)}`;
  await Promise.allSettled(webhooks.map(async (webhook) => {
    const response = await fetch(webhook, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ msgtype: "text", text: { content: `[Weather OPS] ${message}` } })
    });
    if (!response.ok) throw new Error(`OPS webhook ${maskWebhook(webhook)} HTTP ${response.status}`);
  }));
}

export async function notifySuccess(webhooks: string[], slot: string, requestId: string, pagesDeploymentId?: string): Promise<void> {
  const pages = pagesDeploymentId ? `\npages=${pagesDeploymentId}` : "";
  const message = `✅ Weather Report 完成\nslot=${slot}\nrequestId=${requestId}${pages}`;
  await Promise.allSettled(webhooks.map(async (webhook) => {
    const response = await fetch(webhook, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ msgtype: "markdown", markdown: { content: message } })
    });
    if (!response.ok) throw new Error(`OPS webhook ${maskWebhook(webhook)} HTTP ${response.status}`);
  }));
}

export async function notifyFailure(webhooks: string[], stage: string, slot: string, requestId: string, error: unknown): Promise<void> {
  const message = `❌ Weather Report 失败\nstage=${stage}\nslot=${slot}\nrequestId=${requestId}\n${String(error).slice(0, 900)}`;
  await Promise.allSettled(webhooks.map(async (webhook) => {
    const response = await fetch(webhook, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ msgtype: "markdown", markdown: { content: message } })
    });
    if (!response.ok) throw new Error(`OPS webhook ${maskWebhook(webhook)} HTTP ${response.status}`);
  }));
}
