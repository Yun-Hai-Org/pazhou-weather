# EventBridge Weather Dispatcher

用 AWS EventBridge Scheduler（`Asia/Shanghai`）在北京时间 **06:05 / 15:05** 触发 Python 3.12 小 Lambda，调用 GitHub `repository_dispatch`（`event_type=weather-report`），由现有 Weather Report workflow 执行构建/部署/推送。

## 前置

1. 具备部署权限的 AWS 账号与 CLI（`aws cloudformation`）
2. GitHub **长期 PAT**（Fine-grained 推荐）：
   - 目标仓库权限需能创建 `repository_dispatch` / 触发 Actions（通常至少 Contents: Read，以及触发 workflow 所需权限）
   - **禁止**使用会过期的 `gho_` OAuth token
3. 仓库已保留 `on.repository_dispatch.types: [weather-report]`

## 部署

```bash
cd infra/eventbridge-weather

aws cloudformation deploy \
  --stack-name pazhou-weather-dispatcher \
  --template-file template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    GitHubOwner=Yun-Hai-Org \
    GitHubRepo=pazhou-weather \
    GitHubPat='YOUR_GITHUB_PAT'
```

更新 PAT（勿把 token 写入仓库）：

```bash
SECRET_ARN=$(aws cloudformation describe-stacks \
  --stack-name pazhou-weather-dispatcher \
  --query "Stacks[0].Outputs[?OutputKey=='GitHubPatSecretArn'].OutputValue" \
  --output text)

aws secretsmanager put-secret-value \
  --secret-id "$SECRET_ARN" \
  --secret-string 'YOUR_NEW_GITHUB_PAT'
```

## 验证

手动调用 Lambda：

```bash
FN=$(aws cloudformation describe-stacks \
  --stack-name pazhou-weather-dispatcher \
  --query "Stacks[0].Outputs[?OutputKey=='DispatchFunctionName'].OutputValue" \
  --output text)

aws lambda invoke --function-name "$FN" /tmp/weather-dispatch-out.json
cat /tmp/weather-dispatch-out.json
```

然后确认 GitHub Actions 出现由 `repository_dispatch` 触发的 Weather Report run。

## 排障

- Lambda / CloudWatch Logs：查看 GitHub HTTP status 与响应片段
- Scheduler 未触发：检查 Schedule State、Timezone `Asia/Shanghai`、cron `5 6` / `5 15`
- GitHub 401/403：轮换 Secrets Manager 中的 PAT
