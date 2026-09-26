# Hono + Durable Objects Alarm 天气推送架构与决策记录

> 记录时间：2026-09-26
> 范围：`poc/hono-do-alarm/` PoC 的架构、资源评估、新旧方案对比与选型原因

## 新方案

全 Cloudflare 架构，无 GitHub Actions / EventBridge / AWS：

```
Durable Object Alarm（SQLite-backed，06:05/17:05 Asia/Shanghai）
  → Hono Worker（单 Worker 完成全链路）
       1. 拉和风 API（now/24h/7d/warning/air/astronomy）
       2. Hono html 模板字面量渲染详情页
       3. 企微 template_card 推送（多 webhook）
       4. Cloudflare Pages Direct Upload
  → Pages 托管静态页（URL 不变）
```

| 要点 | 说明 |
|---|---|
| 调度 | DO Alarm at-least-once，`alarm()` 内 catch 失败并自重新 `setAlarm()`，不依赖平台重试 |
| 幂等 | DO SQLite 按 `date + am/pm` claim，同 slot 重复触发不重发 |
| 降级 | Pages 上传失败不影响已完成企微推送；holiday/诗词不可用优雅降级 |
| 配置 | 全部迁至 Worker `[vars]` + Secrets，移除 GitHub Secrets / AWS SSM / CloudFormation |

## 资源评估（免费计划）

### CPU（DO Alarm 路径 30s 上限）

| 操作 | CPU |
|---|---|
| 4-6 个和风 API JSON.parse | ~2-5ms |
| Hono 模板字面量渲染 ~100KB HTML | ~1-3ms |
| 卡片 JSON.stringify | <1ms |
| SHA-256（Pages 上传） | <1ms |
| 网络 I/O 等待 | 0（不占 CPU） |
| **合计** | **~5-15ms** |

离 30s 差 3 个数量级。

### 内存（128MB 上限）

HTML ~100KB + JSON 累计 ~200KB + 卡片 ~1KB，峰值 <1MB。

### Wall time（15 分钟上限）

约 10-15 个顺序 I/O，每个 100-500ms，总计 2-5 秒。

### 子请求数（免费 50 个/次）

和风 4-6 + holiday 1 + 诗词 1 + 企微 1-2 + Pages 上传 3-4 + DO 内部 fetch 3-4 ≈ **15-18**，余量充足。

### 注意

手动触发走 `/run`（普通 Worker HTTP），免费计划 CPU 上限仅 **10ms**。如果逻辑接近上限可能触发限流；生产定时走 DO Alarm 30s 路径，不受影响。

## Hono 与 CPU 的关系

Hono 本身就是 TypeScript/JavaScript，编译后是纯 JS，跑在 V8（workerd）上。它的 CPU 消耗与手写原生 fetch handler 基本一样，**不会比 JS 更省**。

CPU 消耗分三层：

| 层级 | 差异来源 |
|---|---|
| 语言/运行时 | **最大差异**。TS/JS（V8）~5-15ms；Python（Pyodide/WASM）50-300ms 冷启动，运行时慢 5-10 倍 |
| 框架 | Hono 几乎为零。轻量路由器，无模板引擎、无反射，开销 <0.1ms |
| 业务逻辑 | JSON.parse、字符串拼接、卡片构建——省不掉 |

新方案总 CPU 5-15ms，绝大部分是业务逻辑，Hono 本身贡献 <1%。选 Hono 不是为了省 CPU，而是为了路由/中间件结构、`html` 模板字面量自动转义、类型安全和生态成熟度。

真正省 CPU 的两个决策：
1. 用 TS/JS 而不是 Python——省掉 Pyodide 冷启动和解释器开销
2. 用原生模板字面量而不是 Jinja2/Handlebars——省掉模板解析运行时

## Python Worker + DO 的可行性

### 结论

CPU/内存大概率够，但有两个结构性风险：

1. **DO 不支持 Python 类**——Cloudflare Python Workers 只能写普通 Worker，DO 类必须用 JS/TS。需要拆成两个项目：Python Worker 做业务逻辑 + TS DO 做调度/幂等，通过 Service Binding 或 HTTP 通信。
2. **冷启动 CPU 计入**——Pyodide 冷启动 50-300ms CPU，DO Alarm 30s 限额下完全可承受，但如果未来逻辑变复杂（重试循环等），Python 解释开销比 TS 高 5-10 倍。

### 资源对比

| | TS（当前方案） | Python |
|---|---|---|
| CPU/内存 | 5-15ms / <1MB | 50-300ms 启动 / 50-80MB |
| DO 支持 | 原生，单项目 | 不支持，需拆两个项目 |
| 代码迁移成本 | 已完成 | 需重写全部逻辑 |
| 维护复杂度 | 1 个部署单元 | 2 个部署单元 + 通信 |

如果团队强烈偏好 Python，可以把业务逻辑迁到 Python Worker，DO 调度层保留 TS。但当前 TS 方案已跑通且余量极大，迁移收益只有"语言偏好"，代价是项目拆分和双部署。

## 旧方案（AWS Lambda）设计时为什么不直接用现在的方案

`sprint-change-proposal-2026-09-23.md`（AWS Lambda 版）已被删除，但替代版本 09-25 中的对比表和 memlog 还原了当时的判断：

1. **DO Alarm 30s CPU 限额的发现时机**——09-23 设计时已知 Worker 免费计划，但认知是"Worker 免费计划 CPU 上限只有 10ms（HTTP 路径）"，不足以跑 Python/Pyodide（冷启动 + Jinja2 要 50-300ms）。所以当时结论是 "Cloudflare Workers + Jinja2 不可行，需要 $5 付费计划"，排除了全 Cloudflare 方案。09-25 重新调研才发现 DO Alarm 路径 CPU 上限是 30 秒，不是 10ms——纯 TS 编排 5-10ms，免费计划完全可行。关键约束变了，方案就变了。

2. **AWS Lambda 方案被用户主动否决**——09-25 提案明确写 "AWS Lambda + Cloudflare Pages Direct Upload | 原推荐，被用户否决"。Agent 当时认为 Lambda 方案架构上最干净（零月费、逻辑清晰），但用户出于简化运维面的考虑，不愿引入 AWS（EventBridge/Lambda/SSM/CloudFormation 已在生产链路制造凭证和多平台故障点），推向了单平台 Cloudflare。

3. **当时没把 Pyodide 从方案中拿掉**——09-23 评估 "Cloudflare Workers + Jinja2（Pyodide）" 时，估算的是 Pyodide 冷启动 + Jinja2 渲染总 CPU，在 10ms 免费计划下确实超限。09-25 不是"让 Python 在 Worker 里跑起来"，而是"把渲染逻辑换成 TS 原生模板字面量"，把 CPU 从百毫秒级降到毫秒级。

一句话总结：旧方案设计时没选现在的方案，不是因为没想到，而是当时对 DO Alarm CPU 限额的认知是 10ms（错误），认为免费计划跑不动任何 Worker 内编排，只能靠 AWS Lambda 做计算；后来发现 DO Alarm 是 30 秒限额且可以用纯 TS 绕开 Pyodide，免费方案可行性判断就翻过来了。

## 新旧方案对比

| | 旧方案（EventBridge + GHA） | 新方案（DO Alarm） |
|---|---|---|
| 调度可靠性 | best-effort，曾连续漏发 | at-least-once + 应用层自重排 |
| 链路长度 | AWS → GitHub → CF Pages，多平台 | 单 Cloudflare Worker |
| 失败模式 | PAT 过期、Pages 401、Cron 零调用 | 外部 API 失败可降级，Pages 失败不阻断推送 |
| 运维面 | 3 平台 Secrets/IaC | 1 平台 wrangler.toml + secrets |
| CPU 限制 | GHA 无限制 | DO Alarm 30s，纯 TS 渲染远低于上限 |

新方案更好，核心优势是消除多平台串联故障点，用 DO Alarm 替换不可靠的 Cron/EventBridge。风险在于 DO 免费计划存储/请求限额极低（每次 `setAlarm` 计 1 row write），但一天 2 次触发完全够用。

## 相关文档

- `docs/weather-report-miss-analysis.md` — 漏发根因分析
- `docs/eventbridge-wecom-migration-lessons.md` — EventBridge 迁移经验
- `_bmad-output/planning-artifacts/sprint-change-proposal-2026-09-25.md` — 方案转向提案
- `_bmad-output/specs/spec-weather-cf-workers/SPEC.md` — 能力契约
- `_bmad-output/planning-artifacts/architecture/ARCHITECTURE-SPINE.md` — 架构脊
