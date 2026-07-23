# 企微天气预报推送

每天北京时间 **05:00**、**15:00** 自动向企业微信群推送广州天气预报，采用 **template_card 图文卡片**（news_notice）展示摘要并跳转到手机端详情页，包括：

- 卡片配图（和风官方图标，按未来 6 小时主导天气自动选择）
- 小时预报 + 日出日落摘要
- 点击跳转手机端详情页（7 板块完整信息）

## 详情页

由 main.py 在后端将和风天气 API 数据内嵌为单文件静态 HTML（手机端优先、深色主题、内联 CSS、和风图标字体 CDN），经 GitHub Actions 部署到 GitHub Pages。详情页 7 板块：

- 当前天气（大字）
- 未来 24 小时逐时（横向滑动）
- 未来 3 天预报
- 空气质量
- 日出日落 + 月相
- 气象预警
- 生活提醒（带伞、空调、衣着、紫外线、感冒、运动、旅游、舒适度、晾晒、防晒、交通、空气扩散）

API Key 仅在后端使用，详情页数据内嵌、不在前端调接口，不暴露 QWEATHER_API_KEY。

## 前置准备

### 1. 和风天气

1. 注册 [和风天气开发者](https://dev.qweather.com/)
2. 创建项目，获取 **API Key** 和 **API Host**（形如 xxx.qweatherapi.com）
3. 免费额度每月 5 万次，本项目每天约 16 次请求，远低于限额

### 2. 企业微信群机器人

1. 在企业微信群中添加「自定义机器人」
2. 复制完整的 Webhook URL
3. 如需同时推送到多个群/多个机器人，将多个 Webhook URL 用英文逗号（,）拼接在同一个 WECOM_WEBHOOK_URL 中即可，例如：

   ```bash
   WECOM_WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=aaa,https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=bbb"
   ```

   程序会依次向每个地址推送同样的卡片；单个地址推送失败不影响其他地址。

## 本地试跑

使用 [uv](https://docs.astral.sh/uv/) 作为运行工具（无需安装第三方依赖，仅用标准库；Python 3.10+）。

```bash
export QWEATHER_API_KEY="你的API_KEY"
export QWEATHER_API_HOST="你的API_HOST"
export WECOM_WEBHOOK_URL="你的企业微信Webhook"
export PAGES_BASE_URL="https://你的用户名.github.io/你的仓库/"   # 可选，卡片跳转地址

./run.sh
```

run.sh 会生成 public/index.html 详情页并向企业微信发送 news_notice 卡片。未设置 PAGES_BASE_URL 时跳转地址回退到默认 Pages 地址。

## 部署到 GitHub Actions

1. 将本仓库 push 到 GitHub：

```bash
git remote add origin 你的仓库地址
git push -u origin main
```

2. 在 GitHub 仓库 **Settings - Secrets and variables - Actions** 中添加：

| Secret              | 说明                         |
| ------------------- | ---------------------------- |
| QWEATHER_API_KEY    | 和风天气 API Key             |
| QWEATHER_API_HOST   | 和风天气 API Host            |
| WECOM_WEBHOOK_URL   | 企业微信群机器人 Webhook URL（多个用英文逗号分隔） |

3. 在 **Settings - Pages** 中将 Source 设为 **GitHub Actions**（workflow 通过 actions/deploy-pages 部署）。

4. weather.yml 的 send-weather job 中已硬编码 PAGES_BASE_URL: https://pr9898.github.io/20260709--/，如需改为自己的 Pages 地址请同步修改。

5. 在 **Actions** 页手动运行 Weather Report workflow 验证，或等待定时触发。send-weather job 发送卡片并生成详情页产物，deploy job 将 public/ 部署到 GitHub Pages。

## 定时说明

| 北京时间 | UTC cron     |
| -------- | ------------ |
| 05:00    | 0 21 * * *   |
| 15:00    | 0 7 * * *    |

## CI（中心化模板）

本仓库通过 [Yun-Hai-Org/ci-templates](https://github.com/Yun-Hai-Org/ci-templates) 的 **Reusable Workflows** 接入统一 CI（方案 B：仓库内 .github/workflows/ci.yml 调用中心化模板）。

- **触发**：Pull Request 与 push 到任意分支时运行 .github/workflows/ci.yml
- **当前启用**：安全扫描（Semgrep / Gitleaks / Trivy 等，按模板默认规则）；可选企业微信 CI 开始/结束通知
- **当前关闭**：静态分析（run-static-analysis: false）、依赖审计（run-dependency-audit: false）——本项目为单脚本结构，无 pyproject.toml，不适用 ruff/pyright/pip-audit 等检查
- **完整文档**：模板能力、参数说明、Secrets 配置见 [ci-templates README](https://github.com/Yun-Hai-Org/ci-templates/blob/main/README.md) 与 templates/python-ci.yml

**Secrets（可选）**

| Secret           | 说明                                                                 |
| ---------------- | -------------------------------------------------------------------- |
| WECOM_BOT_KEY    | 企业微信群机器人 key，用于 CI 通知；建议在组织级配置（见模板 README） |

## 费用

- 和风天气：每月 5 万次内免费
- GitHub Actions / Pages：公开仓库免费
- 企业微信机器人：免费
