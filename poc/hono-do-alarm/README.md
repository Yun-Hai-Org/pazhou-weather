# Hono + Durable Objects Alarm 天气推送 PoC

这个目录是独立 PoC，不修改旧 Python、`infra/` 与 `.github/`。它用 Hono 做 HTTP 编排入口，用 SQLite-backed Durable Object Alarm 做 06:05/17:05 调度、幂等与失败重排。

## 运行前配置

在 `wrangler.toml` 的 `[vars]` 中检查：

- `APP_ENV`：`dev` 或 `prod`
- `QWEATHER_API_HOST`
- `CITY_NAME`、`CITY_LOCATION`、`CITY_COORDS`
- `CLOUDFLARE_ACCOUNT_ID`、`CF_PAGES_PROJECT`、`PUBLIC_BASE_URL`

用 Worker Secret 配置：

```bash
npx wrangler secret put QWEATHER_API_KEY
npx wrangler secret put WECOM_WEBHOOK_URL_PROD
npx wrangler secret put WECOM_WEBHOOK_URL_DEV
npx wrangler secret put CLOUDFLARE_API_TOKEN
```

`WECOM_WEBHOOK_URL_PROD` / `WECOM_WEBHOOK_URL_DEV` 支持逗号、分号或换行分隔多个 webhook。生产与休息日均推送 PROD，只标注当天是“法定工作日”或“休息日”。

## 本地验证

```bash
cd poc/hono-do-alarm
npm install
npx tsc --noEmit
npx wrangler dev
curl http://127.0.0.1:8787/health
```

Dry run 不发送企微：

```bash
WECOM_SKIP_SEND=1 npx wrangler dev
curl -X POST http://127.0.0.1:8787/run -H 'Content-Type: application/json' -d '{"date":"2026-09-25","slot":"am"}'
```

生产部署：

```bash
npx wrangler deploy
curl -X POST https://<worker-domain>/schedule
```

重复调用同一 `date+slot` 的 `/run` 会得到 `duplicate`，不会重复推卡。Pages 上传失败只发 DEV 运维通知，不影响已完成的主推送。

## 资产约定

当前代码引用 `PAGES_BASE_URL` 下的：

- `assets/card/{sun,cloud,rain,snow,thunder,fog}.png`
- `assets/solar-terms/1.png` 到 `24.png`

可复用仓库现有 `assets/card/`，节气图需另行放入 Pages 项目或替换映射。
