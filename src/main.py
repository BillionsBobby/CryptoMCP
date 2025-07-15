"""MCP (Multi-agent Crypto Payment) 主应用
FastAPI + uAgents + Coinremitter + DIA Oracle 集成
"""

import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger

from .core.config import settings
from .core.exceptions import MCPBaseException
from .core.performance import resource_manager
from .core.memory_utils import memory_monitor, resource_cleaner
from .api.routes import router
from .agent.wallet import wallet_agent


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """应用生命周期管理"""
    # 启动时执行
    logger.info("🚀 启动MCP支付系统")
    
    # 创建必要的目录
    import os
    os.makedirs("logs", exist_ok=True)
    
    # 启动性能监控
    memory_monitor.start_monitoring()
    
    # 启动Agent（在后台运行）
    logger.info("启动钱包Agent...")
    agent_task = asyncio.create_task(wallet_agent.run_async())
    
    try:
        # 等待一下确保Agent启动
        await asyncio.sleep(2)
        logger.info("✅ MCP支付系统启动完成")
        
        yield
        
    finally:
        # 关闭时执行
        logger.info("🛑 关闭MCP支付系统")
        
        # 取消Agent任务
        if not agent_task.done():
            agent_task.cancel()
            try:
                await agent_task
            except asyncio.CancelledError:
                pass
        
        # 停止监控和清理资源
        memory_monitor.stop_monitoring()
        await resource_manager.cleanup_all()
        resource_cleaner.cleanup_all()
        
        logger.info("✅ MCP支付系统已关闭")


# 创建FastAPI应用
app = FastAPI(
    title="MCP Crypto Payment",
    description="Multi-agent Crypto Payment module for AI Agents with USDT support",
    version=settings.app_version,
    debug=settings.debug,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:8000", 
        "https://claude.ai",
        "https://*.anthropic.com"
    ] if not settings.debug else ["*"],  # 开发模式允许所有域名，生产模式限制域名
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# 添加请求日志中间件
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """记录请求日志"""
    start_time = asyncio.get_event_loop().time()
    
    # 记录请求
    logger.info(f"📨 {request.method} {request.url.path} - {request.client.host}")
    
    # 处理请求
    response = await call_next(request)
    
    # 计算处理时间
    process_time = asyncio.get_event_loop().time() - start_time
    
    # 记录响应
    logger.info(
        f"📤 {request.method} {request.url.path} - "
        f"状态码: {response.status_code} - "
        f"耗时: {process_time:.3f}s"
    )
    
    return response


# 全局异常处理器
@app.exception_handler(MCPBaseException)
async def mcp_exception_handler(request: Request, exc: MCPBaseException) -> JSONResponse:
    """处理MCP自定义异常"""
    logger.error(f"MCP异常: {exc.message}, 详情: {exc.details}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": exc.__class__.__name__,
            "message": exc.message,
            "details": exc.details,
            "path": str(request.url.path)
        }
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """处理全局异常"""
    logger.error(f"未处理异常: {str(exc)}", exc_info=True)
    
    return JSONResponse(
        status_code=500,
        content={
            "error": "InternalServerError",
            "message": "服务器内部错误",
            "path": str(request.url.path)
        }
    )


# 包含API路由
app.include_router(router)


# 根路径
@app.get("/")
async def root():
    """根路径，返回系统信息"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "status": "running",
        "docs": "/docs",
        "health": "/api/v1/health",
        "agent": {
            "name": wallet_agent.name,
            "address": wallet_agent.address
        }
    }


# 启动信息
@app.on_event("startup")
async def startup_event():
    """启动事件"""
    logger.info(f"🌟 {settings.app_name} v{settings.app_version} 启动")
    logger.info(f"📡 服务地址: http://{settings.host}:{settings.port}")
    logger.info(f"📚 API文档: http://{settings.host}:{settings.port}/docs")


if __name__ == "__main__":
    import uvicorn
    
    # 运行应用
    uvicorn.run(
        "src.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
        log_level="info" if not settings.debug else "debug"
    ) 