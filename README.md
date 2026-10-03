# Pazhou Weather Cloudflare Worker

广州琶洲天气预报推送系统。每天北京时间 06:05 / 17:05 调用天气 API，渲染令牌保护的详情页，写入 KV，并向企业微信推送图文卡片。

## Current architecture

- **Runtime**: Cloudflare Worker + Hono (`poc/hono-do-alarm`)
- **Scheduling and idempotency**: SQLite-backed Durable Object Alarm (`SlotScheduler`)
- **Page and image storage**: `ASSETS` KV namespace
- **Source assets**: [`assets/card/`](assets/card/) is source material for seeding weather icon data into KV
- **Delivery**: WeCom template card plus `/page/:token/detail`

The repository no longer contains the Python runtime, GitHub Actions weather workflow, AWS EventBridge IaC, or Jinja2 templates.

## Production configuration

Non-sensitive runtime settings live in [`poc/hono-do-alarm/wrangler.toml`](poc/hono-do-alarm/wrangler.toml). Sensitive values must be configured as Cloudflare Worker Secrets; do not put them in Git:

```bash
cd poc/hono-do-alarm
npx wrangler secret put QWEATHER_API_KEY
npx wrangler secret put WECOM_WEBHOOK_URL_PROD
npx wrangler secret put WECOM_WEBHOOK_URL_DEV
npx wrangler secret put PUBLIC_PAGE_TOKEN
```

Set these secrets in the target Cloudflare environment before deploy. Local-only copies belong in `.dev.vars`, which is ignored by Git.

## Deploy

```bash
cd poc/hono-do-alarm
npx wrangler deploy
curl -X POST https://<worker-domain>/schedule
```

## Schedule

The Worker cron triggers are UTC `5 22 * * *` and `5 9 * * *`, corresponding to Asia/Shanghai 06:05 and 17:05. The Durable Object claims a `date + slot`, runs the alarm path, and prevents duplicate sends for that slot.

## Verify

```bash
cd poc/hono-do-alarm
npm run typecheck
npx wrangler deploy --dry-run --outdir /tmp/hono-do-alarm-dryrun
curl http://127.0.0.1:8787/health
```

Use `npx wrangler dev` for the local health check.

## Cloudflare Pages rollback status

The existing Cloudflare Pages resources may remain temporarily for rollback or assets until explicitly migrated. This repository does not use Cloudflare Pages Direct Upload.
