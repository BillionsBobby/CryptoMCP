# FinAgent MCP Server - 云端部署指南

本文档提供FinAgent MCP服务器的完整云端部署指南，支持Google Cloud Run、AWS Lambda、Azure Container Instances等多种云平台。

## 🎯 概述

FinAgent MCP服务器现已优化支持云端托管，具备以下特性：

- ✅ **Streamable HTTP传输** - 符合MCP规范的HTTP协议
- ✅ **容器化部署** - 使用Docker进行一致性部署
- ✅ **身份验证** - 支持Bearer Token、API Key等多种认证方式
- ✅ **健康检查** - 内置监控和健康检查端点
- ✅ **环境配置** - 灵活的环境变量配置
- ✅ **高可用性** - 支持自动扩缩容和故障恢复

## 📋 前置要求

### 通用要求
- Docker Desktop 或 Docker Engine
- Git
- 网络连接

### Google Cloud Run
- Google Cloud SDK (`gcloud`)
- Google Cloud项目和计费账户
- Cloud Run API、Cloud Build API、Artifact Registry API

### AWS Lambda/ECS
- AWS CLI
- AWS账户和IAM权限
- ECR访问权限

### Azure Container Instances
- Azure CLI
- Azure订阅
- Container Registry权限

## 🚀 快速开始

### 方法1：使用自动化脚本（推荐）

```bash
# 克隆项目
git clone https://github.com/your-org/FinAgent.git
cd FinAgent

# 设置环境变量
export PROJECT_ID="your-gcp-project-id"
export AUTH_TOKEN="your-secure-token"

# 一键部署到Google Cloud Run
./deploy/cloud-run-deploy.sh
```

### 方法2：手动部署

#### 构建Docker镜像
```bash
# 构建镜像
docker build -f Dockerfile.cloud -t finagent-mcp-server .

# 测试本地运行
docker run -p 8080:8080 \
  -e AUTH_TOKEN="test-token" \
  finagent-mcp-server
```

#### 推送到容器注册表
```bash
# Google Container Registry
docker tag finagent-mcp-server gcr.io/PROJECT_ID/finagent-mcp-server
docker push gcr.io/PROJECT_ID/finagent-mcp-server

# AWS ECR
aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com
docker tag finagent-mcp-server YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/finagent-mcp-server
docker push YOUR_ACCOUNT.dkr.ecr.us-east-1.amazonaws.com/finagent-mcp-server
```

## ☁️ 平台特定部署

### Google Cloud Run

#### 使用自动化脚本
```bash
# 基础部署
PROJECT_ID=my-project ./deploy/cloud-run-deploy.sh

# 带认证的部署
PROJECT_ID=my-project AUTH_TOKEN=secure123 ./deploy/cloud-run-deploy.sh

# 自定义配置
PROJECT_ID=my-project \
REGION=europe-west1 \
SERVICE_NAME=finagent-prod \
AUTH_TOKEN=secure123 \
./deploy/cloud-run-deploy.sh
```

#### 手动部署
```bash
# 启用API
gcloud services enable run.googleapis.com cloudbuild.googleapis.com

# 构建和部署
gcloud builds submit --tag gcr.io/PROJECT_ID/finagent-mcp-server
gcloud run deploy finagent-mcp-server \
  --image gcr.io/PROJECT_ID/finagent-mcp-server \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars="AUTH_TOKEN=your-token"
```

### AWS ECS/Fargate

```bash
# 创建任务定义
aws ecs register-task-definition --cli-input-json file://deploy/aws-task-definition.json

# 创建服务
aws ecs create-service \
  --cluster finagent-cluster \
  --service-name finagent-mcp-server \
  --task-definition finagent-mcp-server \
  --desired-count 1
```

### Azure Container Instances

```bash
# 创建资源组
az group create --name finagent-rg --location eastus

# 部署容器
az container create \
  --resource-group finagent-rg \
  --name finagent-mcp-server \
  --image finagent-mcp-server \
  --dns-name-label finagent-mcp \
  --ports 8080 \
  --environment-variables AUTH_TOKEN=your-token
```

## 🔧 配置说明

### 环境变量

| 变量名 | 描述 | 默认值 | 必需 |
|--------|------|--------|------|
| `HOST` | 监听地址 | `0.0.0.0` | 否 |
| `PORT` | 监听端口 | `8080` | 否 |
| `DEBUG` | 调试模式 | `false` | 否 |
| `AUTH_TOKEN` | 认证令牌 | 无 | 推荐 |
| `API_KEY` | API密钥 | 无 | 可选 |
| `COINREMITTER_API_KEY` | Coinremitter API密钥 | `demo_key` | 生产必需 |
| `CORS_ORIGINS` | CORS允许的源 | `*` | 否 |

### 完整配置示例

```bash
# 生产环境配置
export HOST="0.0.0.0"
export PORT="8080"
export DEBUG="false"
export AUTH_TOKEN="prod-token-$(openssl rand -hex 16)"
export API_KEY="fa_$(openssl rand -hex 24)"
export COINREMITTER_API_KEY="your-real-api-key"
export CORS_ORIGINS="https://your-client-domain.com"
export LOG_LEVEL="INFO"
```

## 🔒 安全配置

### 认证设置

```bash
# 生成安全令牌
export AUTH_TOKEN=$(openssl rand -hex 32)

# 生成API密钥
export API_KEY="fa_$(openssl rand -hex 24)"

# 生成JWT密钥
export JWT_SECRET=$(openssl rand -hex 32)
```

### 网络安全

```yaml
# Cloud Run安全配置
spec:
  template:
    metadata:
      annotations:
        run.googleapis.com/ingress: all
        run.googleapis.com/ingress-status: all
    spec:
      containerConcurrency: 1000
      serviceAccountName: finagent-service-account
```

### 防火墙规则

```bash
# Google Cloud防火墙
gcloud compute firewall-rules create allow-finagent-mcp \
  --allow tcp:8080 \
  --source-ranges 0.0.0.0/0 \
  --description "Allow FinAgent MCP Server"
```

## 📊 监控和日志

### 健康检查

服务提供以下端点用于监控：

- **健康检查**: `GET /health`
- **根信息**: `GET /`
- **MCP端点**: `GET|POST /mcp`

```bash
# 健康检查示例
curl https://your-service-url.com/health

# 响应示例
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z",
  "version": "1.0.0",
  "transport": "streamable-http",
  "auth_enabled": true
}
```

### 日志配置

```python
# 结构化日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "json",
    "fields": {
        "timestamp": True,
        "level": True,
        "message": True,
        "service": "finagent-mcp-server"
    }
}
```

### 指标收集

```bash
# Prometheus指标端点（如果启用）
curl https://your-service-url.com/metrics
```

## 🔧 客户端配置

### Claude Desktop配置

```json
{
  "mcpServers": {
    "finagent-cloud": {
      "url": "https://your-service-url.com/mcp",
      "transport": "streamable-http",
      "description": "FinAgent云端MCP服务器",
      "headers": {
        "Authorization": "Bearer your-auth-token"
      }
    }
  }
}
```

### 编程方式连接

```python
from fastmcp import Client

# 连接到云端MCP服务器
async with Client(
    "https://your-service-url.com/mcp",
    headers={"Authorization": "Bearer your-auth-token"}
) as client:
    # 列出可用工具
    tools = await client.list_tools()
    print(f"可用工具: {[tool.name for tool in tools]}")
    
    # 调用创建支付工具
    result = await client.call_tool("create_payment", {
        "amount_usd": 100.0,
        "network": "trc20",
        "description": "测试支付"
    })
    print(f"支付结果: {result}")
```

### 认证代理

对于需要认证的服务，可以使用云平台的代理：

```bash
# Google Cloud Run代理
gcloud run services proxy finagent-mcp-server --region=us-central1

# 然后连接到本地代理
# URL: http://localhost:8080/mcp
```

## 🚨 故障排除

### 常见问题

#### 1. 服务无法启动
```bash
# 检查日志
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=finagent-mcp-server" --limit 50

# 检查配置
gcloud run services describe finagent-mcp-server --region=us-central1
```

#### 2. 认证失败
```bash
# 验证令牌
curl -H "Authorization: Bearer your-token" https://your-service-url.com/health

# 检查环境变量
gcloud run services describe finagent-mcp-server --region=us-central1 --format="value(spec.template.spec.template.spec.containers[0].env[].value)"
```

#### 3. 网络连接问题
```bash
# 测试连通性
curl -v https://your-service-url.com/

# 检查防火墙规则
gcloud compute firewall-rules list --filter="name~'finagent'"
```

### 调试技巧

```bash
# 启用调试模式
gcloud run services update finagent-mcp-server \
  --region=us-central1 \
  --set-env-vars="DEBUG=true"

# 查看实时日志
gcloud logging tail "resource.type=cloud_run_revision AND resource.labels.service_name=finagent-mcp-server"

# 测试本地容器
docker run -it --rm -p 8080:8080 \
  -e DEBUG=true \
  -e AUTH_TOKEN=test \
  finagent-mcp-server
```

## 🔄 更新和维护

### 滚动更新

```bash
# 构建新版本
docker build -f Dockerfile.cloud -t finagent-mcp-server:v1.1.0 .

# 推送镜像
docker tag finagent-mcp-server:v1.1.0 gcr.io/PROJECT_ID/finagent-mcp-server:v1.1.0
docker push gcr.io/PROJECT_ID/finagent-mcp-server:v1.1.0

# 更新服务
gcloud run deploy finagent-mcp-server \
  --image gcr.io/PROJECT_ID/finagent-mcp-server:v1.1.0 \
  --region us-central1
```

### 备份和恢复

```bash
# 导出服务配置
gcloud run services describe finagent-mcp-server \
  --region=us-central1 \
  --format="export" > finagent-service-backup.yaml

# 恢复服务
gcloud run services replace finagent-service-backup.yaml \
  --region=us-central1
```

### 版本管理

```bash
# 标记版本
gcloud run services update-traffic finagent-mcp-server \
  --region=us-central1 \
  --to-revisions=finagent-mcp-server-v1-1-0=50,finagent-mcp-server-v1-0-0=50

# 完全切换到新版本
gcloud run services update-traffic finagent-mcp-server \
  --region=us-central1 \
  --to-latest
```

## 📈 性能优化

### 资源配置

```bash
# 优化内存和CPU
gcloud run deploy finagent-mcp-server \
  --memory=2Gi \
  --cpu=2 \
  --concurrency=2000 \
  --max-instances=100
```

### 冷启动优化

```bash
# 设置最小实例数
gcloud run deploy finagent-mcp-server \
  --min-instances=1 \
  --max-instances=10
```

### 缓存策略

```python
# 应用级缓存
CACHE_CONFIG = {
    "redis_url": "redis://your-redis-instance",
    "default_ttl": 300,
    "price_data_ttl": 60
}
```

## 🌍 多区域部署

### 全球负载均衡

```bash
# 部署到多个区域
REGIONS=("us-central1" "europe-west1" "asia-northeast1")

for region in "${REGIONS[@]}"; do
  gcloud run deploy finagent-mcp-server-$region \
    --image gcr.io/PROJECT_ID/finagent-mcp-server \
    --region $region \
    --allow-unauthenticated
done
```

### DNS配置

```bash
# 创建全球负载均衡器
gcloud compute backend-services create finagent-backend \
  --global \
  --protocol=HTTPS

# 添加后端
gcloud compute backend-services add-backend finagent-backend \
  --global \
  --network-endpoint-group=finagent-neg-us \
  --network-endpoint-group-region=us-central1
```

## 💰 成本优化

### 资源使用优化

```bash
# 设置合理的并发和实例限制
gcloud run deploy finagent-mcp-server \
  --concurrency=1000 \
  --max-instances=10 \
  --cpu-throttling
```

### 按需扩缩容

```yaml
# 自动扩缩容配置
metadata:
  annotations:
    autoscaling.knative.dev/minScale: "0"
    autoscaling.knative.dev/maxScale: "100"
    autoscaling.knative.dev/target: "70"
```

## 📞 支持和贡献

- **GitHub Issues**: [项目Issues页面](https://github.com/your-org/FinAgent/issues)
- **文档**: [完整文档](https://your-docs-site.com)
- **社区**: [讨论区](https://github.com/your-org/FinAgent/discussions)

### 贡献指南

1. Fork项目仓库
2. 创建功能分支: `git checkout -b feature/cloud-enhancement`
3. 提交更改: `git commit -m "Add cloud deployment feature"`
4. 推送分支: `git push origin feature/cloud-enhancement`
5. 创建Pull Request

---

## 📄 许可证

本项目采用MIT许可证 - 查看[LICENSE](LICENSE)文件了解详情。

**FinAgent MCP Server** - 让AI代理轻松处理加密货币支付 🚀 