# Hono + Durable Objects Alarm 天气推送

这个目录是当前生产 Worker。它用 Hono 做 HTTP 编排入口，用 SQLite-backed Durable Object Alarm 做 06:05/17:05 调度、幂等与失败重排。

## 运行前配置

在 `wrangler.toml` 的 `[vars]` 中维护非敏感运行时配置：

- `APP_ENV`：当前固定为 `prod`
- `QWEATHER_API_HOST`
- `CITY_NAME`、`CITY_LOCATION`、`CITY_COORDS`
- `PUBLIC_BASE_URL`
- `WECOM_SKIP_SEND`、`FORCE_HOURLY_RUN`

以下值不得写入 `wrangler.toml` 或 Git，必须用 Worker Secret 配置：

- `QWEATHER_API_KEY`
- `WECOM_WEBHOOK_URL_PROD`
- `WECOM_WEBHOOK_URL_DEV`
- `PUBLIC_PAGE_TOKEN`

```bash
npx wrangler secret put QWEATHER_API_KEY
npx wrangler secret put WECOM_WEBHOOK_URL_PROD
npx wrangler secret put WECOM_WEBHOOK_URL_DEV
npx wrangler secret put PUBLIC_PAGE_TOKEN
```

秘密只保存在 Cloudflare Worker Secret 中。部署前需要在目标环境完成设置；未设置的必需秘密会让运行路径显式失败，而不是回退到占位值。

`WECOM_WEBHOOK_URL_PROD` / `WECOM_WEBHOOK_URL_DEV` 支持逗号、分号或换行分隔多个 webhook。生产与休息日均推送 PROD，只标注当天是“法定工作日”或“休息日”。

## 本地开发秘密

复制 `.dev.vars.example` 为 `.dev.vars`，再填入本机真实值。`.dev.vars` 和其他本地秘密文件已被 `.gitignore` 忽略，不要提交。

```bash
cp .dev.vars.example .dev.vars
```

## 本地验证

```bash
cd poc/hono-do-alarm
npm install
npx tsc --noEmit
npx wrangler dev
curl http://127.0.0.1:8787/health
```

Dry run 不发送企微。也可在 `.dev.vars` 中临时设置 `WECOM_SKIP_SEND=1`：

```bash
npx wrangler dev
curl -X POST http://127.0.0.1:8787/run -H 'Content-Type: application/json' -d '{"date":"2026-10-03","slot":"am"}'
```

Wrangler cron 为 UTC `22:05` / `09:05`，对应 Asia/Shanghai 的 `06:05` / `17:05`。触发时 Worker 请求 `SLOT_DO` 声明同一 `date+slot`，Durable Object Alarm 负责排程和防重复。重复调用同一 `date+slot` 的 `/run` 会得到 `duplicate`，不会重复推卡。

生产部署：

```bash
npx wrangler deploy
curl -X POST https://<worker-domain>/schedule
```

当前页面存储使用绑定为 `ASSETS` 的 KV：`/run` 会把详情 HTML 写入 `index.html`，`/page/:token/detail` 按公开页令牌校验后读取；`/page/:token/assets/card/*.png` 和 `/page/:token/assets/solar-terms/*.jpg` 也从同一 KV 返回。这里不是 Cloudflare Pages Direct Upload。页面 KV 写入失败只发 DEV 运维通知，不影响已完成的主推送。

## 资产约定

当前 Worker 从 `ASSETS` KV 读取：

- `assets/card/{sun,cloud,rain,snow,thunder,fog}.png`
- `assets/solar-terms/1.jpg` 到 `24.jpg`

可复用仓库现有 `assets/card/`；节气图需另行导入 `ASSETS` KV，或替换代码中的资产映射。
