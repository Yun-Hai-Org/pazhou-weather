# 天气预报漏发问题分析与改进建议

> **架构更新（2026-08-08）：** 定时调度已迁至 **AWS EventBridge Scheduler**（见仓库根目录 README 与 `infra/eventbridge-weather/`）；下文仍保留调查当时基于 Cloudflare Worker Cron 的分析记录。


> 调查时间：2026-08-06（北京时间）  
> 范围：约 2026-07-30 至 2026-08-06  
> 仓库：[Yun-Hai-Org/pazhou-weather](https://github.com/Yun-Hai-Org/pazhou-weather)

## 1. 结论摘要

最近漏发**不是单一原因**，而是链路多段串联故障叠加：

| 层级 | 问题 | 典型表现 |
|------|------|----------|
| Cloudflare Cron | 定时未触发 | Worker 无调用记录，GitHub 无 `repository_dispatch` |
| Worker → GitHub | `GH_PAT` 调 GitHub 失败 | Worker `scriptThrewException`，GHA 不出现 |
| GitHub Actions | 构建/部署失败 | 有 run 但失败，企业微信步骤被跳过 |
| 应用代码 | 第三方 API 字段变更 | 构建崩溃（如 AQI `primaryPollutant`） |
| 可观测性 | Logs/Traces 关闭、无告警 | 出问题后只能事后人工查 |

**今天早上（2026-08-06 06:05）漏发原因：** Cloudflare Worker Cron **未产生任何调用**（与昨天下午同类），不是企业微信或和风天气本身的问题。

---

## 2. 当前架构（简要）

```
北京 06:05 / 17:05
    → CF Worker Cron（UTC 5 22 * * * / 5 9 * * *）
    → repository_dispatch(event_type=weather-report)
    → GitHub Actions「Weather Report」
         1) 构建详情页（含配图，失败可回退）
         2) 部署 Cloudflare Pages
         3) 推送企业微信 template_card
```

关键依赖：

- Worker Secrets：`GH_OWNER` / `GH_REPO` / `GH_PAT`
- GHA Secrets：`QWEATHER_*`、`WECOM_WEBHOOK_URL_*`、`CLOUDFLARE_API_TOKEN` 等
- 外部：和风天气、Pollinations 配图、企业微信机器人

---

## 3. 近期事件时间线（北京时间）

| 时间 | 期望 | 实际 | 根因归类 |
|------|------|------|----------|
| 07-30 17:05 | 定时推送 | GHA 失败 | 依赖安装（清华镜像 403）等历史问题 |
| 08-03 06:05 | 定时推送 | 成功 | — |
| **08-03 17:05** | 定时推送 | **漏发** | Worker 触发成功，但 **Pages 部署 401**（`CLOUDFLARE_API_TOKEN` 失效），Send WeCom 被跳过 |
| 08-03 晚 | 补救 | 已 Roll CF Token 并手动成功 | Token 运维 |
| 08-04 06:05 | 定时推送 | 成功 | — |
| **08-04 17:05** | 定时推送 | **漏发** | Cron 已触发，Worker **`scriptThrewException`**（调 GitHub dispatch 非 2xx，高度怀疑当时 `GH_PAT`） |
| 08-04 晚 | 补救 | 刷新 Worker `GH_PAT`（曾用 `gh` OAuth `gho_` 临时代替） | 凭证脆弱 |
| 08-05 06:05 | 定时推送 | 成功 | — |
| **08-05 17:05** | 定时推送 | **漏发** | Cron **零调用**（调度配置仍在，但未执行） |
| 08-05 晚 | 补救 | 手动 dispatch → 构建因 **AQI `primaryPollutant` 对象** 崩溃；修代码后补发成功并合入 main（PR #6） | 代码脆弱 + Cron 漏触发 |
| **08-06 06:05** | 定时推送 | **漏发** | Cron **再次零调用**（与 08-05 下午同类） |

### 证据摘录

**Worker 调用（Cloudflare Analytics）**

| UTC 时段 | 对应北京 | 状态 |
|----------|----------|------|
| 2026-08-04T09:05 | 08-04 17:05 | `scriptThrewException`（1 subrequest） |
| 2026-08-04T22:05 | 08-05 06:05 | `success` |
| 2026-08-05T09:05 | 08-05 17:05 | **无记录** |
| 2026-08-05T22:05 | 08-06 06:05 | **无记录** |

**Cron 配置（调查时仍存在）**

- `5 22 * * *` → 北京 06:05
- `5 9 * * *` → 北京 17:05

**GHA 失败样例**

- [run 30799907929](https://github.com/Yun-Hai-Org/pazhou-weather/actions/runs/30799907929)：`Cloudflare API returned non-200: 401 Authentication error`
- [run 30995094984](https://github.com/Yun-Hai-Org/pazhou-weather/actions/runs/30995094984)：`AttributeError: 'dict' object has no attribute 'upper'`（空气质量）

---

## 4. 根因分类

### 4.1 Cloudflare Cron 漏触发（当前最致命）

- **现象：** 调度条目仍在，但目标时刻无 Worker invocation。
- **影响：** 整条链路静默中断，GitHub / 企业微信都不会动。
- **背景：** CF Cron 属于平台侧调度；`wrangler secret put` 会生成新 version（08-04、08-05 多次更新 `GH_PAT`）。不能排除 secret 部署与 Cron 执行之间的平台异常或间歇漏触发，但**即使配置正确也可能偶发漏跑**，需要应用层兜底。
- **现状短板：** Worker Observability（Logs / Traces）为 **Disabled**，无法看到异常正文。

### 4.2 Worker `GH_PAT` 脆弱

- Worker 仅在 GitHub 返回非 2xx 时抛错；Logs 关闭时看不到具体 `status/body`。
- 曾用 `gh auth token`（`gho_` OAuth）写入 Worker Secret：可短期恢复，但**会过期/失效**，不适合长期 Cron。
- 失败时无重试、无告警。

### 4.3 GHA 步骤耦合导致「部署失败 = 不推送」

`weather.yml` 中：

- Deploy 使用 `if: always()`；
- **Send WeCom 默认 `if: success()`**。

因此：构建失败或 Deploy 失败时，**企业微信不会发送**（即使天气数据已拉到）。  
08-03 下午即为此模式：Token 401 → 未推送。

### 4.4 外部 API 契约变更无防护

和风 `airquality/v1` 的 `primaryPollutant` 从字符串变为 `{code,name,fullName}`，直接导致构建崩溃。  
配图（Pollinations）频繁 500/429，虽可回退静态图，但重试拉长流水线（可达 10+ 分钟），放大超时与并发失败风险。

### 4.5 密钥与运维

| Secret | 问题 |
|--------|------|
| `CLOUDFLARE_API_TOKEN` | 曾突然 401（Pages 权限 Token），需人工 Roll |
| `GH_PAT` | 不宜用短期 OAuth；应用长期 fine-grained/classic PAT，并设轮换提醒 |
| Observability | 关闭 → 事后排查成本高 |

### 4.6 无「应发未发」监控

链路成功完全依赖「人有没有在群里看到消息」。缺少：

- 定时槽位巡检（06:10 / 17:10 是否已有成功 run）
- 失败自动通知（企业微信/邮件）
- Cron 心跳或二次触发

---

## 5. 改进建议（按优先级）

### P0 — 立刻做（恢复可靠性）

1. **更换并固化 Worker `GH_PAT`**
   - 使用 GitHub **Fine-grained PAT** 或 Classic PAT（权限：目标仓库可触发 `repository_dispatch` / workflow）。
   - **禁止**再使用 `gh auth` 的 `gho_` OAuth。
   - 设置到期提醒（日历/密码管理器）；到期前 7 天轮换。

2. **重新 `wrangler deploy` Worker**
   - 在确认 `wrangler.toml` cron 仍为 `5 22 * * *`、`5 9 * * *` 后完整部署一次，避免仅 secret 更新后的版本状态异常。
   - 部署后手动触发一次 Worker `fetch`，确认能产生 GHA run。

3. **打开 Worker Observability**
   - 启用 Workers Logs（至少 Errors）；保留 08-04 类 `scriptThrewException` 的 message。

4. **补发今天早上**
   - `gh workflow run "Weather Report"`（或 repository_dispatch），确认生产群收到。

### P1 — 短期（本周）

5. **解耦「推送」与「部署」**
   - Send WeCom 改为在构建成功后执行，**不依赖** Pages Deploy 成功；或 Deploy 失败时仍允许推送（卡片图可用静态/上次 CDN）。
   - 目标：Pages 挂了，群消息仍能发。

6. **增加漏发巡检**
   - 另设 Cron（可仍用 CF Worker，或 GitHub `schedule`）在 06:20 / 17:20 检查：
     - 最近 30 分钟内是否存在 conclusion=success 的 Weather Report；
     - 若无 → 自动 `workflow_dispatch` 补发 + 告警。
   - 这是对抗「CF Cron 静默漏触发」最有效的兜底。

7. **GHA 失败告警**
   - 现有 CI 已有 WeCom notify；Weather Report 失败时同样通知（含 run URL）。

8. **配图降级策略收紧**
   - 减少重试次数/总等待（例如最多 3 次或总计 ≤60s），尽快回退静态图，避免拖垮整 job。

### P2 — 中期（架构加固）

9. **减少单点**
   - 评估：GitHub `schedule` 直接触发 Weather Report（与 CF Cron 双通道，幂等去重：同一半天同一 slot 只发一次）。
   - 或 Worker 失败时本地重试 2～3 次（指数退避）再抛错。

10. **契约测试 / 冒烟**
    - 对和风 now/24h/airquality/indices 做最小 schema 断言（如 `primaryPollutant` 允许 dict|null）。
    - PR / 每日一次 dry-run（`WECOM_SKIP_SEND=1`）跑通构建。

11. **密钥台账**
    - 文档化：名称、权限、到期日、轮换人、上次验证日期（`CLOUDFLARE_API_TOKEN`、`GH_PAT`、和风 Key）。

12. **幂等与去重**
    - 以「日期 + 时段（am/pm）」为 key，避免巡检补发与迟到 Cron 双发。

---

## 6. 建议落地顺序（可执行清单）

- [ ] 创建长期 `GH_PAT` → `wrangler secret put GH_PAT`
- [ ] `cd workers/weather-cron && bunx wrangler deploy`
- [ ] 开启 Worker Logs
- [ ] 手动跑通一次 Weather Report（验证今早缺口）
- [ ] 改 `weather.yml`：推送不依赖 Deploy 成功
- [ ] 增加 06:20 / 17:20 漏发巡检 + 失败告警
- [ ] 缩短配图重试
- [ ] （可选）GitHub `schedule` 双通道

---

## 7. 今日早上结论（单独说明）

**2026-08-06 06:05 漏发 = Cloudflare `weather-cron` 在该时刻未执行（Analytics 零调用）。**

不是：

- 企业微信限流（无对应 GHA）
- 和风 API（无对应 GHA）
- AQI 代码 bug（该 bug 已在 08-05 合入 main，且今早根本没有跑到 GHA）

与 **2026-08-05 17:05** 属于同一类：**Cron 静默漏触发**。在缺少巡检兜底前，会继续偶发。

---

## 8. 参考链接

- Workflow：`.github/workflows/weather.yml`
- Worker：`workers/weather-cron/`
- AQI 修复：PR #6 `fix: 适配和风 AQI primaryPollutant 对象结构`
- 手动成功补发示例：[run 30996372074](https://github.com/Yun-Hai-Org/pazhou-weather/actions/runs/30996372074)
