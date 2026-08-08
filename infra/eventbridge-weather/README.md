# EventBridge Weather Dispatcher

EventBridge Scheduler（`Asia/Shanghai`，北京 **06:05 / 15:05**）→ Lambda → GitHub `repository_dispatch`。

GitHub PAT 存在 **SSM Parameter Store SecureString（Standard，永久免费）**，不使用 Secrets Manager，避免按月收费。

> 说明：当前账号下 CloudFormation 无法直接创建 `SecureString`（Early Validation 失败），因此 PAT 用 CLI 写入 SSM，模板只引用参数名。

## 前置

1. AWS CLI（区域建议 `us-west-2`），部署身份需 IAM / Lambda / Scheduler / SSM 权限  
2. Fine-grained PAT（单仓库 Contents: Read and write）  
3. 仓库保留 `repository_dispatch: [weather-report]`

## 部署 / 迁移

```bash
export AWS_REGION=us-west-2
PARAM=/pazhou-weather-dispatcher/github-pat

# 1) 写入免费 SecureString（新建或覆盖）
aws ssm put-parameter \
  --name "$PARAM" \
  --type SecureString \
  --value 'YOUR_GITHUB_PAT' \
  --overwrite

# 2) 部署/更新栈（不再需要把 PAT 传给 CloudFormation）
cd infra/eventbridge-weather
aws cloudformation deploy \
  --region us-west-2 \
  --stack-name pazhou-weather-dispatcher \
  --template-file template.yaml \
  --capabilities CAPABILITY_NAMED_IAM \
  --parameter-overrides \
    GitHubOwner=Yun-Hai-Org \
    GitHubRepo=pazhou-weather \
    PatParameterName="$PARAM"
```

若从旧版 Secrets Manager 迁移：先用 `get-secret-value` 取出 PAT，再执行上面的 `put-parameter`，然后 `cloudformation deploy`（模板会删除 Secrets Manager 资源）。

## 验证

```bash
FN=$(aws cloudformation describe-stacks \
  --region us-west-2 \
  --stack-name pazhou-weather-dispatcher \
  --query "Stacks[0].Outputs[?OutputKey=='DispatchFunctionName'].OutputValue" \
  --output text)

aws lambda invoke --region us-west-2 --function-name "$FN" /tmp/weather-dispatch-out.json
cat /tmp/weather-dispatch-out.json
```

## 排障

- CloudWatch Logs：`/aws/lambda/pazhou-weather-dispatcher-dispatch`
- Scheduler：`pazhou-weather-dispatcher-morning` / `-afternoon`
- 401/403：检查 SSM 参数中的 PAT
