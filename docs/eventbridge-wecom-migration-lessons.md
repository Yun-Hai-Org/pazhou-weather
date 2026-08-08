# EventBridge 调度迁移与企微运维通知：实践经验

> 整理时间：2026-08-08  
> 仓库：[Yun-Hai-Org/pazhou-weather](https://github.com/Yun-Hai-Org/pazhou-weather)  
> 相关：漏发根因见 [`weather-report-miss-analysis.md`](./weather-report-miss-analysis.md)；部署步骤见 [`../infra/eventbridge-weather/README.md`](../infra/eventbridge-weather/README.md)

本文记录从「漏发治理 → EventBridge 调度 → 运维 markdown 通知」全过程中确认过的决策、踩坑与可复用做法，便于后续排障与轮换密钥。

---

## 1. 背景与目标

漏发调查表明问题是**多段串联**，其中 Cloudflare Worker Cron **静默零调用**与 PAT 失效是高频项。目标收口为：

| 目标 | 做法 |
|------|------|
| 调度可靠、可观测 | AWS EventBridge Scheduler → 小 Lambda → GitHub `repository_dispatch` |
| 唯一定时源 | **去掉** GHA `schedule`，避免双通道双发 |
| 成败可感知 | Weather Report 成功/失败都向 **DEV 企微群**发 markdown |
| 周末不打扰生产群 | `APP_ENV=prod` + 周末时天气卡片改发 DEV，不跳过、不发 PROD |
| 控制成本 | PAT 用 SSM SecureString（Standard），不用 Secrets Manager |

---

## 2. 最终架构（已落地）

```
北京 06:05 / 15:05（Asia/Shanghai）
  → EventBridge Scheduler（us-west-2）
  → Lambda: pazhou-weather-dispatcher-dispatch
  → GitHub API repository_dispatch (event_type=weather-report)
  → GHA「Weather Report」
       1) 构建详情页（WECOM_SKIP_SEND=1）
       2) 部署 Cloudflare Pages
       3) 发送天气 template_card（周末 → DEV）
       4) notify-wecom 运维 markdown（始终 DEV）
```

| 组件 | 值 |
|------|-----|
| AWS 账号 | `947921574020`（YunHai） |
| Region | **us-west-2（Oregon）** |
| Stack | `pazhou-weather-dispatcher` |
| Schedules | `…-morning` / `…-afternoon`，`cron(5 6 * * ? *)` / `cron(5 15 * * ? *)` |
| PAT 存储 | SSM `/pazhou-weather-dispatcher/github-pat`（SecureString Standard） |
| 触发事件 | `repository_dispatch` → notify 文案「外部调度」 |

**Region 与本机无关：** 定时运行时由 **Lambda 所在 Region** 出网调 `api.github.com`；本机/代理只影响你本地 CLI 部署与测延迟，不影响每天定时链路。

---

## 3. 关键决策（已确认）

### 3.1 调度方案

| 方案 | 结论 |
|------|------|
| Scheduler → Lambda → GitHub API | **采用**：可打日志、失败明确、可手动 Invoke |
| Scheduler → API Destination 直调 GitHub | 否：排障弱，类似旧 Worker「黑盒 HTTP」 |
| 保留 GHA `schedule` 双通道 | **否**：需幂等去重；用户要求唯一定时源 |

不必为「三云」（AWS / GitHub / Cloudflare）强行收敛到单一平台：当前是薄调度 + GHA 主计算 + 静态页托管。痛点是凭证/调度静默失败，不是平台数量本身。

### 3.2 运维通知

| 项 | 结论 |
|----|------|
| 格式 | 复用 `.github/actions/notify-wecom` **markdown**（与 CI 同款） |
| 目标群 | **DEV** |
| 密钥 | 用完整 Webhook：`WECOM_WEBHOOK_URL_DEV`（**不要**单独再维护 `WECOM_BOT_KEY`） |
| 失败策略 | 通知失败只打 warning，**不拖垮** Weather Report job |

### 3.3 周末行为

`WECOM_SKIP_PROD_WEEKENDS=1`（`repository_dispatch` 时打开）+ `APP_ENV=prod`：

- **不要**整次跳过发送
- **不要**继续发 PROD
- **要**把天气卡片发到 DEV（`resolve_webhook_urls()`）

运维 markdown 与周末无关，始终走 `WECOM_WEBHOOK_URL_DEV`。

### 3.4 推送时刻

北京 **06:05 / 15:05**（曾讨论过 05:55/16:55，最终与业务约定对齐为整点后 5 分）。

---

## 4. 落地 PR 时间线

| PR | 内容 |
|----|------|
| [#9](https://github.com/Yun-Hai-Org/pazhou-weather/pull/9) | 去 GHA schedule；成败 notify；EventBridge CFN；周末改发 DEV |
| [#10](https://github.com/Yun-Hai-Org/pazhou-weather/pull/10) | 运维通知改用 `WECOM_WEBHOOK_URL_DEV`；PAT → SSM，去掉 Secrets Manager |
| [#11](https://github.com/Yun-Hai-Org/pazhou-weather/pull/11) | `notify-wecom` 改 urllib（修 curl network error） |
| [#12](https://github.com/Yun-Hai-Org/pazhou-weather/pull/12) | 仅同步已 squash 分支 tip（清理用，无功能变更） |

验证样例（卡片 + 运维 markdown 均到 DEV）：

- [run 31258685758](https://github.com/Yun-Hai-Org/pazhou-weather/actions/runs/31258685758)  
  日志关键句：`WeCom notification sent: ✅ Weather Report 完成 (http=200)`

---

## 5. AWS / 凭证经验

### 5.1 Secrets Manager → SSM

- Secrets Manager 有**按密钥按月**费用，本项目一天两次触发不划算。
- SSM Parameter Store **SecureString + Standard** 对这类少量密钥通常**零费用**。
- **坑：** 当前账号下 CloudFormation **不能**直接创建 `SecureString`（Early Validation 失败）。  
  **做法：** CLI `aws ssm put-parameter` 写入；模板只引用参数名 `PatParameterName`。

### 5.2 PAT

- 用 Fine-grained PAT（例名：`pazhou-weather-eventbridge`），单仓库 Contents: Read and write。
- 旧 CF Worker / classic token（如 `weather-cron-dispatch`）在 Worker 停用后应删除，避免多 PAT 并存难审计。
- 栈**不是**一次性资源：删掉 CloudFormation 栈会停掉调度。

### 5.3 部署身份 vs 运行身份

- 可用临时 IAM 用户/Access Key 做 `cloudformation deploy`；**日常定时不依赖**该 Key。
- 运行时用 Lambda 执行角色读 SSM、调 GitHub。

### 5.4 手动验证

```bash
export AWS_REGION=us-west-2
aws lambda invoke \
  --function-name pazhou-weather-dispatcher-dispatch \
  --cli-binary-format raw-in-base64-out \
  --payload '{"source":"manual-verify"}' \
  /tmp/weather-dispatch-out.json
cat /tmp/weather-dispatch-out.json   # 期望含 "status": 204
```

排障：CloudWatch `/aws/lambda/pazhou-weather-dispatcher-dispatch`；401/403 先查 SSM 里的 PAT。

---

## 6. 企微通知：天气卡片能到、运维 markdown 不到

### 6.1 现象

- DEV 群收到天气 `template_card`
- 收不到「Weather Report 完成」markdown
- Job 仍为绿色；旧日志类似：`WeCom webhook returned errcode=-1 errmsg=curl network error`

### 6.2 根因

| 路径 | 传输 | 结果 |
|------|------|------|
| 天气卡片（`main.py`） | Python `urllib` | 成功 |
| 运维 notify（旧 `action.yml`） | shell `curl`，且 stderr 被吞 | 瞬间失败，只打 warning |

同一 runner、同一 `WECOM_WEBHOOK_URL_DEV`，**不是 Secret 没配**，是 **curl 在该环境下对企微 webhook 不可靠**。

### 6.3 修复（可复用）

1. 抽出 `.github/actions/notify-wecom/notify.py`，用与 `main.py` **相同**的 `urllib` POST。
2. Webhook 字符串做规范化：按 `,;`/换行拆分，取第一个 `https://` URL（与业务侧多 URL 习惯一致）。
3. 错误打 `::warning::`，不 `exit 1`。
4. composite action 用 `python3 "${{ github.action_path }}/notify.py"`；`ubuntu-latest` 自带 python3。

成功日志应类似：

```text
WeCom notification sent: ✅ Weather Report 完成 (http=200)
```

**经验法则：** 同一目标若一条链路已用 urllib/httpx 跑通，运维通知不要另起一套 curl，除非有充分验证。

---

## 7. Git / 分支清理经验（本仓库 hooks）

本仓库开启了若干 Cursor / 本地 hooks，清理 squash 合并后的分支时容易卡住：

| 约束 | 表现 |
|------|------|
| 禁止本地直接 merge 进 `main` | 必须走 PR |
| 仓库只允许 **squash** merge | merge commit 被 GitHub 拒绝 |
| squash 后 tip **不是** main 祖先 | `--merged` 查询 / 删除门禁仍认为「未合并」 |
| 强制去掉本地分支 / 去掉远程分支 | 门禁拦截「未合并」分支 |
| worktree 仍 checkout 该分支 | `gh pr merge --delete-branch` 清本地失败 |

**有效清理顺序（内容已在 main 上确认后）：**

1. 确认远程 tip 与 `origin/main` **无独有功能 diff**（或功能已由 squash PR 合入）。
2. 在 `main` 上把本地功能分支指针挪到 `origin/main`（`branch -f <name> origin/main`），使 tip 成为 main 祖先。
3. 先去掉远程同名分支，再 `fetch --prune`，再用安全方式去掉本地分支。
4. 先让 worktree 离开该分支（或移除 worktree），再清理分支。
5. 不要用「再开一个会回退代码的 PR」去合旧 tip：旧分支落后 main 时，`merge-tree` 可能把 **curl 版 notify** 等旧内容冲突回来。

真正还没合入的功能，仍应正常开 PR；**已 squash 的分支不要再当功能分支合并**。

---

## 8. 密钥与 Secret 台账（迁移后）

| 名称 | 用途 | 备注 |
|------|------|------|
| `WECOM_WEBHOOK_URL_DEV` | 天气（周末/dev）+ **运维 markdown** | 完整 URL |
| `WECOM_WEBHOOK_URL_PROD` | 工作日生产多群 | 逗号分隔 |
| SSM `/pazhou-weather-dispatcher/github-pat` | EventBridge Lambda 调 GitHub | 勿再依赖 Secrets Manager |
| ~~`WECOM_BOT_KEY`~~ | 曾计划给运维 notify | **已弃用**，勿再依赖 |
| 旧 Worker `GH_PAT` | CF Cron | Worker 停用后删除 |

Weather Report **不再**使用 GHA `schedule`；勿把 schedule 加回去，除非同时做幂等去重。

---

## 9. 验证清单（以后改调度/通知时照做）

- [ ] `aws lambda invoke` → JSON 含 GitHub `204`
- [ ] Actions 出现 `repository_dispatch` /「外部调度」的 Weather Report
- [ ] DEV 收到天气 `template_card`
- [ ] DEV 收到「Weather Report 完成」或失败 markdown
- [ ] 运维步骤日志为 `WeCom notification sent: … (http=200)`，无 `curl network error`
- [ ] 周末：PROD 无卡片；DEV 有卡片 + 运维消息
- [ ] 工作日：PROD 有卡片；DEV 仍有运维消息

---

## 10. 仍可改进（未做，避免过度设计）

漏发分析里的部分项仍有价值，但本次未一并做：

- 推送与 Pages 部署进一步解耦（Deploy 失败仍发卡片）
- 漏发巡检（如 06:20 / 15:20 检查最近成功 run）
- 配图重试上限收紧
- 和风 API 契约/冒烟测试

有新漏发时：先看 EventBridge/Lambda 日志是否触发 → 再看 GHA conclusion → 再看企微两条路径（卡片 vs markdown）是否都成功。

---

## 11. 关键路径速查

| 用途 | 路径 |
|------|------|
| Workflow | `.github/workflows/weather.yml` |
| 运维通知 action | `.github/actions/notify-wecom/`（`action.yml` + `notify.py`） |
| 周末 URL 解析 | `main.py` → `resolve_webhook_urls()` |
| IaC | `infra/eventbridge-weather/template.yaml` |
| 部署说明 | `infra/eventbridge-weather/README.md` |
| 漏发调查（历史） | `docs/weather-report-miss-analysis.md` |
