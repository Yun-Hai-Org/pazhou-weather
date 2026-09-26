export function maskWebhook(url: string): string {
  try {
    const parsed = new URL(url);
    const key = parsed.searchParams.get("key") || "";
    if (!key) return `${parsed.origin}${parsed.pathname}`;
    const masked = key.length > 8 ? `${key.slice(0, 4)}...${key.slice(-4)}` : "*".repeat(key.length);
    parsed.searchParams.set("key", masked);
    return parsed.toString();
  } catch {
    return "<invalid-webhook>";
  }
}

export function hourOnly(fxTime: string | undefined): string {
  return fxTime ? fxTime.slice(11, 16) : "--";
}
