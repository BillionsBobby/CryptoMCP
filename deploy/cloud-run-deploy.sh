#!/bin/bash
# FinAgent MCP Server - Google Cloud Run 部署脚本
# 自动化部署FinAgent MCP服务器到Google Cloud Run

set -e  # 遇到错误立即退出

# ==================== 配置变量 ====================
PROJECT_ID=${PROJECT_ID:-"your-project-id"}
REGION=${REGION:-"us-central1"}
SERVICE_NAME=${SERVICE_NAME:-"finagent-mcp-server"}
REPOSITORY_NAME=${REPOSITORY_NAME:-"mcp-servers"}

# 镜像标签
IMAGE_TAG=${IMAGE_TAG:-"latest"}
IMAGE_URL="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY_NAME}/${SERVICE_NAME}:${IMAGE_TAG}"

# 认证配置
AUTH_TOKEN=${AUTH_TOKEN:-""}
API_KEY=${API_KEY:-""}

# ==================== 颜色输出 ====================
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# ==================== 预检查 ====================
check_prerequisites() {
    log_info "检查部署先决条件..."
    
    # 检查gcloud命令
    if ! command -v gcloud &> /dev/null; then
        log_error "gcloud CLI未安装，请先安装Google Cloud SDK"
        exit 1
    fi
    
    # 检查Docker
    if ! command -v docker &> /dev/null; then
        log_error "Docker未安装，请先安装Docker"
        exit 1
    fi
    
    # 检查项目ID
    if [[ "$PROJECT_ID" == "your-project-id" ]]; then
        log_error "请设置正确的PROJECT_ID环境变量"
        exit 1
    fi
    
    log_success "先决条件检查完成"
}

# ==================== Google Cloud 设置 ====================
setup_gcloud() {
    log_info "配置Google Cloud..."
    
    # 设置项目
    gcloud config set project "$PROJECT_ID"
    
    # 启用必要的API
    log_info "启用必要的Google Cloud API..."
    gcloud services enable \
        cloudbuild.googleapis.com \
        run.googleapis.com \
        artifactregistry.googleapis.com
    
    log_success "Google Cloud配置完成"
}

# ==================== Artifact Registry 设置 ====================
setup_artifact_registry() {
    log_info "设置Artifact Registry..."
    
    # 创建仓库（如果不存在）
    if ! gcloud artifacts repositories describe "$REPOSITORY_NAME" \
        --location="$REGION" &> /dev/null; then
        
        log_info "创建Artifact Registry仓库..."
        gcloud artifacts repositories create "$REPOSITORY_NAME" \
            --repository-format=docker \
            --location="$REGION" \
            --description="FinAgent MCP服务器容器仓库"
    else
        log_info "Artifact Registry仓库已存在"
    fi
    
    # 配置Docker认证
    gcloud auth configure-docker "${REGION}-docker.pkg.dev"
    
    log_success "Artifact Registry设置完成"
}

# ==================== 构建和推送镜像 ====================
build_and_push_image() {
    log_info "构建和推送Docker镜像..."
    
    # 回到项目根目录
    cd "$(dirname "$0")/.."
    
    # 使用Cloud Build构建镜像
    log_info "使用Cloud Build构建镜像: $IMAGE_URL"
    gcloud builds submit \
        --region="$REGION" \
        --tag="$IMAGE_URL" \
        --file="Dockerfile.cloud" \
        .
    
    log_success "镜像构建和推送完成"
}

# ==================== 部署到Cloud Run ====================
deploy_to_cloud_run() {
    log_info "部署到Cloud Run..."
    
    # 基础部署命令
    DEPLOY_CMD="gcloud run deploy $SERVICE_NAME \
        --image=$IMAGE_URL \
        --region=$REGION \
        --platform=managed \
        --allow-unauthenticated \
        --port=8080 \
        --memory=1Gi \
        --cpu=1 \
        --min-instances=0 \
        --max-instances=10 \
        --concurrency=1000 \
        --timeout=300"
    
    # 添加环境变量
    ENV_VARS="HOST=0.0.0.0,PORT=8080,DEBUG=false"
    
    if [[ -n "$AUTH_TOKEN" ]]; then
        ENV_VARS="$ENV_VARS,AUTH_TOKEN=$AUTH_TOKEN"
        log_info "已配置认证令牌"
    else
        log_warning "未配置认证令牌，服务将允许无认证访问"
    fi
    
    if [[ -n "$API_KEY" ]]; then
        ENV_VARS="$ENV_VARS,API_KEY=$API_KEY"
        log_info "已配置API密钥"
    fi
    
    # 执行部署
    $DEPLOY_CMD --set-env-vars="$ENV_VARS"
    
    log_success "Cloud Run部署完成"
}

# ==================== 获取服务信息 ====================
get_service_info() {
    log_info "获取服务信息..."
    
    # 获取服务URL
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)")
    
    echo ""
    log_success "部署成功！"
    echo "=========================================="
    echo "服务名称: $SERVICE_NAME"
    echo "服务URL:  $SERVICE_URL"
    echo "MCP端点:  $SERVICE_URL/mcp"
    echo "健康检查: $SERVICE_URL/health"
    echo "区域:     $REGION"
    echo "项目:     $PROJECT_ID"
    echo "=========================================="
    
    # 生成客户端配置
    echo ""
    log_info "客户端配置示例:"
    echo "{"
    echo "  \"mcpServers\": {"
    echo "    \"finagent-cloud\": {"
    echo "      \"url\": \"$SERVICE_URL/mcp\","
    echo "      \"transport\": \"streamable-http\","
    echo "      \"description\": \"FinAgent云端MCP服务器\""
    if [[ -n "$AUTH_TOKEN" ]]; then
        echo "      \"headers\": {"
        echo "        \"Authorization\": \"Bearer $AUTH_TOKEN\""
        echo "      }"
    fi
    echo "    }"
    echo "  }"
    echo "}"
}

# ==================== 测试部署 ====================
test_deployment() {
    log_info "测试部署..."
    
    SERVICE_URL=$(gcloud run services describe "$SERVICE_NAME" \
        --region="$REGION" \
        --format="value(status.url)")
    
    # 测试健康检查端点
    if curl -s "$SERVICE_URL/health" > /dev/null; then
        log_success "健康检查端点正常"
    else
        log_error "健康检查端点无响应"
        return 1
    fi
    
    # 测试根端点
    if curl -s "$SERVICE_URL/" > /dev/null; then
        log_success "根端点正常"
    else
        log_error "根端点无响应"
        return 1
    fi
    
    log_success "部署测试通过"
}

# ==================== 主函数 ====================
main() {
    echo "🚀 开始部署FinAgent MCP服务器到Google Cloud Run"
    echo "项目: $PROJECT_ID"
    echo "区域: $REGION"
    echo "服务: $SERVICE_NAME"
    echo ""
    
    check_prerequisites
    setup_gcloud
    setup_artifact_registry
    build_and_push_image
    deploy_to_cloud_run
    get_service_info
    test_deployment
    
    echo ""
    log_success "🎉 FinAgent MCP服务器部署完成！"
}

# ==================== 帮助信息 ====================
show_help() {
    echo "FinAgent MCP Server - Google Cloud Run 部署脚本"
    echo ""
    echo "用法: $0 [选项]"
    echo ""
    echo "环境变量:"
    echo "  PROJECT_ID         Google Cloud项目ID (必需)"
    echo "  REGION            部署区域 (默认: us-central1)"
    echo "  SERVICE_NAME      服务名称 (默认: finagent-mcp-server)"
    echo "  REPOSITORY_NAME   仓库名称 (默认: mcp-servers)"
    echo "  IMAGE_TAG         镜像标签 (默认: latest)"
    echo "  AUTH_TOKEN        认证令牌 (可选)"
    echo "  API_KEY           API密钥 (可选)"
    echo ""
    echo "示例:"
    echo "  PROJECT_ID=my-project ./deploy/cloud-run-deploy.sh"
    echo "  PROJECT_ID=my-project AUTH_TOKEN=secret123 ./deploy/cloud-run-deploy.sh"
    echo ""
}

# ==================== 命令行参数处理 ====================
case "${1:-}" in
    -h|--help)
        show_help
        exit 0
        ;;
    *)
        main "$@"
        ;;
esac 