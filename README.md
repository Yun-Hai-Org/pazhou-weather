# 企微天气预报推送

每天北京时间 **06:00**、**18:00** 自动向企业微信群推送广州天气预报，包括：

- 实况天气
- 未来 3 小时逐小时预报
- 未来 24 小时概略
- 灾害天气预警
- 生活提醒（带伞、空调、衣着、紫外线、感冒）

## 前置准备

### 1. 和风天气

1. 注册 [和风天气开发者](https://dev.qweather.com/)
2. 创建项目，获取 **API Key** 和 **API Host**（形如 `xxx.qweatherapi.com`）
3. 免费额度每月 5 万次，本项目每天约 8 次请求，远低于限额

### 2. 企业微信群机器人

1. 在企业微信群中添加「自定义机器人」
2. 复制完整的 Webhook URL
3. 如需同时推送到多个群/多个机器人，将多个 Webhook URL 用英文逗号（`,`）拼接在同一个
   `WECOM_WEBHOOK_URL` 中即可，例如：

   ```bash
   WECOM_WEBHOOK_URL="https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=aaa,https://qyapi.weixin.qq.com/cgi-bin/webhook/send?key=bbb"
   ```

   程序会依次向每个地址推送同样的天气播报内容；单个地址推送失败不影响其他地址。

## 本地试跑

无需安装第三方依赖（Python 3.10+）。

```bash
export QWEATHER_API_KEY="你的API_KEY"
export QWEATHER_API_HOST="你的API_HOST"
export WECOM_WEBHOOK_URL="你的企业微信Webhook"

./run.sh
```

## 部署到 GitHub Actions

1. 将本仓库 push 到 GitHub：

```bash
git remote add origin <你的仓库地址>
git push -u origin main
```

2. 在 GitHub 仓库 **Settings → Secrets and variables → Actions** 中添加：

| Secret              | 说明                         |
| ------------------- | ---------------------------- |
| `QWEATHER_API_KEY`  | 和风天气 API Key             |
| `QWEATHER_API_HOST` | 和风天气 API Host            |
| `WECOM_WEBHOOK_URL` | 企业微信群机器人 Webhook URL（多个用英文逗号分隔） |

3. 在 **Actions** 页手动运行 `Weather Report` workflow 验证，或等待定时触发。

## 定时说明

| 北京时间 | UTC cron     |
| -------- | ------------ |
| 06:00    | `0 22 * * *` |
| 18:00    | `0 10 * * *` |

## 费用

- 和风天气：每月 5 万次内免费
- GitHub Actions：公开仓库免费
- 企业微信机器人：免费
