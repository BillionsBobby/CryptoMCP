#!/usr/bin/env python3
"""FinAgent HTTP MCP Server
专为云端托管设计的Model Context Protocol服务器
支持Streamable HTTP传输、容器化部署和身份验证
"""

import asyncio
import os
import json
from datetime import datetime
from typing import List, Optional, Dict, Any
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base
from pydantic import BaseModel, Field
from loguru import logger


# 创建FastMCP服务器，支持HTTP传输
mcp = FastMCP(
    name="FinAgent-HTTP",
    description="FinAgent MCP服务器 - 云端托管版本，支持加密货币支付和市场数据"
)


# ==================== 配置管理 ====================

@dataclass
class ServerConfig:
    """服务器配置"""
    host: str = "0.0.0.0"  # 云端部署需要监听所有接口
    port: int = int(os.getenv("PORT", "8080"))  # 使用环境变量或默认端口
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # API配置
    coinremitter_api_key: str = os.getenv("COINREMITTER_API_KEY", "demo_key")
    dia_oracle_url: str = os.getenv("DIA_ORACLE_URL", "https://api.diadata.org/v1/assetQuotation/Ethereum/0xdAC17F958D2ee523a2206206994597C13D831ec7")
    
    # 认证配置
    auth_token: Optional[str] = os.getenv("AUTH_TOKEN")
    
    def __post_init__(self):
        """初始化后处理"""
        self.cors_origins: List[str] = os.getenv("CORS_ORIGINS", "*").split(",")


config = ServerConfig()


# ==================== 数据模型 ====================

class PaymentParams(BaseModel):
    """创建支付参数"""
    amount_usd: float = Field(description="USD金额", gt=0)
    network: str = Field(description="网络类型 (trc20/erc20)", default="trc20")
    description: Optional[str] = Field(description="支付描述", default=None)


class PaymentResult(BaseModel):
    """支付结果"""
    success: bool = Field(description="操作是否成功")
    invoice_id: Optional[str] = Field(description="发票ID", default=None)
    payment_address: Optional[str] = Field(description="支付地址", default=None)
    amount_usdt: Optional[float] = Field(description="USDT数量", default=None)
    amount_usd: Optional[float] = Field(description="USD金额", default=None)
    qr_code: Optional[str] = Field(description="二维码URL", default=None)
    error: Optional[str] = Field(description="错误信息", default=None)


class BalanceResult(BaseModel):
    """余额查询结果"""
    success: bool = Field(description="操作是否成功")
    balance: Optional[float] = Field(description="余额", default=None)
    network: Optional[str] = Field(description="网络类型", default=None)
    error: Optional[str] = Field(description="错误信息", default=None)


class PriceResult(BaseModel):
    """价格查询结果"""
    success: bool = Field(description="操作是否成功")
    price: Optional[float] = Field(description="USDT价格", default=None)
    timestamp: Optional[str] = Field(description="时间戳", default=None)
    error: Optional[str] = Field(description="错误信息", default=None)


# ==================== 模拟数据 ====================

# 模拟价格数据
MOCK_USDT_PRICE = 0.9998

# 模拟发票存储
MOCK_INVOICES: Dict[str, Dict[str, Any]] = {}

# 模拟余额数据
MOCK_BALANCES = {
    "trc20": 1000.0,
    "erc20": 850.5
}


def generate_invoice_id() -> str:
    """生成发票ID"""
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    import random
    return f"INV_{timestamp}_{random.randint(1000, 9999)}"


def generate_mock_address(network: str) -> str:
    """生成模拟地址"""
    if network.lower() == "trc20":
        return "TR" + "x" * 32
    elif network.lower() == "erc20":
        return "0x" + "x" * 40
    else:
        return "UNKNOWN_NETWORK"


# ==================== MCP Tools ====================

@mcp.tool()
async def create_payment(params: PaymentParams, ctx: Context) -> PaymentResult:
    """创建USDT支付发票
    
    根据USD金额创建加密货币支付发票，支持TRC20和ERC20网络
    """
    try:
        logger.info(f"创建支付: ${params.amount_usd} USD, 网络: {params.network}")
        
        # 验证参数
        if params.amount_usd <= 0:
            raise ValueError("金额必须大于0")
        
        if params.network.lower() not in ["trc20", "erc20"]:
            raise ValueError("网络类型必须是trc20或erc20")
        
        # 计算USDT数量（使用模拟价格）
        usdt_amount = params.amount_usd / MOCK_USDT_PRICE
        logger.debug(f"计算得出USDT数量: {usdt_amount}")
        
        # 生成发票信息
        invoice_id = generate_invoice_id()
        payment_address = generate_mock_address(params.network)
        
        # 存储发票信息
        MOCK_INVOICES[invoice_id] = {
            "amount_usd": params.amount_usd,
            "amount_usdt": usdt_amount,
            "network": params.network,
            "address": payment_address,
            "description": params.description,
            "status": "pending",
            "created_at": datetime.now().isoformat()
        }
        
        logger.info(f"支付发票创建成功: {invoice_id}")
        
        return PaymentResult(
            success=True,
            invoice_id=invoice_id,
            payment_address=payment_address,
            amount_usdt=usdt_amount,
            amount_usd=params.amount_usd,
            qr_code=f"https://chart.googleapis.com/chart?chs=200x200&cht=qr&chl={payment_address}"
        )
        
    except Exception as e:
        error_msg = f"创建支付失败: {str(e)}"
        logger.error(error_msg)
        return PaymentResult(success=False, error=error_msg)


@mcp.tool()
async def check_balance(network: str, ctx: Context) -> BalanceResult:
    """检查钱包余额
    
    查询指定网络的USDT余额
    """
    try:
        logger.info(f"查询{network}余额")
        
        # 验证网络类型
        if network.lower() not in ["trc20", "erc20"]:
            raise ValueError("网络类型必须是trc20或erc20")
        
        # 获取余额
        balance = MOCK_BALANCES.get(network.lower(), 0.0)
        
        logger.info(f"{network}余额: {balance} USDT")
        
        return BalanceResult(
            success=True,
            balance=balance,
            network=network
        )
        
    except Exception as e:
        error_msg = f"查询余额失败: {str(e)}"
        logger.error(error_msg)
        return BalanceResult(success=False, error=error_msg)


@mcp.tool()
async def get_usdt_price(ctx: Context) -> PriceResult:
    """获取USDT价格
    
    获取当前USDT对USD的价格
    """
    try:
        logger.info("获取USDT价格")
        
        # 使用模拟价格数据
        price = MOCK_USDT_PRICE
        timestamp = datetime.now().isoformat()
        
        logger.info(f"USDT价格: ${price}")
        
        return PriceResult(
            success=True,
            price=price,
            timestamp=timestamp
        )
        
    except Exception as e:
        error_msg = f"获取价格失败: {str(e)}"
        logger.error(error_msg)
        return PriceResult(success=False, error=error_msg)


@mcp.tool()
async def list_invoices(ctx: Context) -> Dict[str, Any]:
    """列出所有支付发票
    
    返回所有创建的支付发票列表
    """
    try:
        logger.info("获取发票列表")
        
        invoices = []
        for invoice_id, invoice_data in MOCK_INVOICES.items():
            invoices.append({
                "invoice_id": invoice_id,
                "amount_usd": invoice_data["amount_usd"],
                "amount_usdt": invoice_data["amount_usdt"],
                "network": invoice_data["network"],
                "status": invoice_data["status"],
                "created_at": invoice_data["created_at"]
            })
        
        return {
            "success": True,
            "invoices": invoices,
            "total_count": len(invoices)
        }
        
    except Exception as e:
        error_msg = f"获取发票列表失败: {str(e)}"
        logger.error(error_msg)
        return {"success": False, "error": error_msg}


# ==================== MCP Resources ====================

@mcp.resource("payment://invoice/{invoice_id}")
async def get_payment_status(invoice_id: str) -> str:
    """获取支付发票状态
    
    查询指定发票ID的支付状态和详细信息
    """
    try:
        if invoice_id not in MOCK_INVOICES:
            return f"错误: 发票 {invoice_id} 不存在"
        
        invoice = MOCK_INVOICES[invoice_id]
        return f"""# 支付发票状态

**发票ID**: {invoice_id}
**状态**: {invoice['status']}
**金额**: ${invoice['amount_usd']} USD / {invoice['amount_usdt']:.4f} USDT
**网络**: {invoice['network'].upper()}
**支付地址**: {invoice['address']}
**创建时间**: {invoice['created_at']}

## 支付说明
请向上述地址发送 **{invoice['amount_usdt']:.4f} USDT** 来完成支付。
"""
        
    except Exception as e:
        return f"错误: {str(e)}"


@mcp.resource("market://usdt/info")
async def get_market_info() -> str:
    """获取USDT市场信息
    
    提供USDT的当前市场数据和统计信息
    """
    try:
        return f"""# USDT 市场信息

## 基本信息
- **代币名称**: Tether USD
- **符号**: USDT
- **当前价格**: ${MOCK_USDT_PRICE:.4f}
- **更新时间**: {datetime.now().isoformat()}

## 网络支持
- **TRC20** (Tron): 低手续费，快速确认
- **ERC20** (Ethereum): 广泛支持，流动性高

## 用途
- 稳定币交易
- DeFi协议
- 跨境支付
- 价值存储
"""
        
    except Exception as e:
        return f"错误: {str(e)}"


@mcp.resource("config://networks")
async def get_supported_networks() -> str:
    """获取支持的网络配置
    
    返回所有支持的区块链网络配置信息
    """
    return """# 支持的区块链网络

## TRC20 (Tron)
- **网络名称**: TRON
- **代币标准**: TRC20
- **区块确认**: 19确认
- **平均确认时间**: 3分钟
- **手续费**: 超低 (~1 TRX)

## ERC20 (Ethereum)
- **网络名称**: Ethereum
- **代币标准**: ERC20
- **区块确认**: 12确认
- **平均确认时间**: 2-5分钟
- **手续费**: 中等 (取决于网络拥堵)

## 推荐使用
对于小额支付，推荐使用 **TRC20** 网络，手续费更低。
对于大额支付，推荐使用 **ERC20** 网络，安全性更高。
"""


# ==================== MCP Prompts ====================

@mcp.prompt(title="创建支付")
def create_payment_prompt(amount: str, currency: str = "USD") -> List[base.Message]:
    """创建支付请求的提示模板"""
    return [
        base.UserMessage(f"我需要创建一个{amount} {currency}的支付发票"),
        base.AssistantMessage("我来帮您创建支付发票。请告诉我："),
        base.AssistantMessage("1. 您希望使用哪个网络？(TRC20推荐用于小额，ERC20用于大额)"),
        base.AssistantMessage("2. 这笔支付的用途描述是什么？"),
        base.UserMessage("请为我生成支付发票")
    ]


@mcp.prompt(title="余额查询")
def balance_inquiry_prompt(network: str = "trc20") -> str:
    """余额查询的提示模板"""
    return f"""请帮我查询{network.upper()}网络的USDT余额。

如果余额充足，我可能需要进行以下操作：
- 发送USDT到其他地址
- 创建新的支付发票
- 查看交易历史

请先显示当前余额。"""


@mcp.prompt(title="市场分析")
def market_analysis_prompt(timeframe: str = "1h") -> List[base.Message]:
    """市场分析的提示模板"""
    return [
        base.UserMessage("我想了解USDT的当前市场情况"),
        base.AssistantMessage("我来为您分析USDT的市场数据："),
        base.AssistantMessage("1. 首先获取当前价格信息"),
        base.AssistantMessage("2. 分析价格稳定性"),
        base.AssistantMessage("3. 提供投资建议"),
        base.UserMessage(f"请分析{timeframe}时间框架内的数据")
    ]


# ==================== 健康检查 ====================

@mcp.tool()
async def health_check(ctx: Context) -> Dict[str, Any]:
    """健康检查
    
    检查服务器状态和连接性
    """
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0",
        "transport": "streamable-http",
        "host": config.host,
        "port": config.port
    }


# ==================== 认证中间件 ====================

async def authenticate_request(headers: Dict[str, str]) -> bool:
    """验证请求身份
    
    Args:
        headers: HTTP请求头
        
    Returns:
        bool: 是否通过验证
    """
    if not config.auth_token:
        return True  # 未配置认证令牌时允许所有请求
    
    auth_header = headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        return token == config.auth_token
    
    return False


# ==================== 日志配置 ====================

def setup_cloud_logging():
    """配置云端日志"""
    import sys
    logger.remove()  # 移除默认处理器
    
    # 添加结构化日志输出（适合云端）
    logger.add(
        sys.stdout,
        level="INFO" if not config.debug else "DEBUG",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=False,  # 云端环境通常不需要颜色
    )

# 初始化日志
setup_cloud_logging()

# ==================== 运行服务器 ====================

def main():
    """MCP服务器入口点"""
    logger.info(f"🚀 启动FinAgent HTTP MCP服务器")
    logger.info(f"📍 监听地址: {config.host}:{config.port}")
    logger.info(f"🔧 调试模式: {config.debug}")
    
    if config.auth_token:
        logger.info("🔒 身份验证已启用")
    else:
        logger.warning("⚠️  身份验证未启用")
    
    try:
        # 设置环境变量以配置主机和端口
        os.environ["HOST"] = config.host
        os.environ["PORT"] = str(config.port)
        
        # 使用streamable-http传输运行MCP服务器
        mcp.run(transport="streamable-http")
    except Exception as e:
        logger.error(f"❌ 服务器启动失败: {e}")
        raise


def run_server():
    """同步入口点"""
    main()


if __name__ == "__main__":
    run_server() 