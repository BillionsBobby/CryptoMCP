"""FinAgent MCP Server
基于官方MCP Python SDK的Model Context Protocol服务器
提供加密货币支付工具、市场数据资源和提示模板
"""

import asyncio
import os
from contextlib import asynccontextmanager
from typing import AsyncIterator, Dict, Any, Optional, List
from dataclasses import dataclass

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base
from pydantic import BaseModel, Field
from loguru import logger

from .core.config import settings
from .core.models import NetworkType, PaymentStatus
from .services.coinremitter import coinremitter_service
from .services.dia_oracle import dia_oracle_service


@dataclass
class ServerContext:
    """服务器上下文，存储初始化的服务"""
    coinremitter: Any
    dia_oracle: Any


@asynccontextmanager
async def server_lifespan(server: FastMCP) -> AsyncIterator[ServerContext]:
    """管理MCP服务器生命周期"""
    logger.info("🚀 启动FinAgent MCP服务器")
    
    # 创建必要的目录
    os.makedirs("logs", exist_ok=True)
    
    # 初始化服务
    try:
        yield ServerContext(
            coinremitter=coinremitter_service,
            dia_oracle=dia_oracle_service
        )
    finally:
        logger.info("🛑 关闭FinAgent MCP服务器")


# 创建FastMCP服务器
mcp = FastMCP(
    name="FinAgent",
    description="AI Agent的加密货币支付和市场数据服务",
    lifespan=server_lifespan
)


# ==================== MCP Tools ====================

class CreatePaymentParams(BaseModel):
    """创建支付参数"""
    amount_usd: float = Field(description="USD金额")
    network: str = Field(description="网络类型 (trc20/erc20)", default="trc20")
    description: Optional[str] = Field(description="支付描述", default=None)


class PaymentResult(BaseModel):
    """支付结果"""
    success: bool
    invoice_id: Optional[str] = None
    payment_address: Optional[str] = None
    amount_usdt: Optional[float] = None
    amount_usd: Optional[float] = None
    qr_code: Optional[str] = None
    error: Optional[str] = None


@mcp.tool()
async def create_payment(params: CreatePaymentParams, ctx: Context) -> PaymentResult:
    """创建USDT支付发票
    
    根据USD金额创建加密货币支付发票，支持TRC20和ERC20网络
    """
    try:
        await ctx.info(f"创建支付: ${params.amount_usd} USD, 网络: {params.network}")
        
        # 验证网络类型
        network = NetworkType(params.network.lower())
        
        # 获取USDT价格并计算数量
        usdt_amount = await dia_oracle_service.calculate_usdt_amount(params.amount_usd)
        await ctx.debug(f"计算得出USDT数量: {usdt_amount}")
        
        # 创建支付发票
        payment = await coinremitter_service.create_invoice(
            amount=usdt_amount,
            network=network,
            description=params.description or f"FinAgent payment ${params.amount_usd}"
        )
        
        await ctx.info(f"支付发票创建成功: {payment.invoice_id}")
        
        return PaymentResult(
            success=True,
            invoice_id=payment.invoice_id,
            payment_address=payment.address,
            amount_usdt=payment.amount,
            amount_usd=params.amount_usd,
            qr_code=payment.qr_code
        )
        
    except Exception as e:
        error_msg = f"创建支付失败: {str(e)}"
        await ctx.error(error_msg)
        return PaymentResult(success=False, error=error_msg)


class SendCryptoParams(BaseModel):
    """发送加密货币参数"""
    amount: float = Field(description="USDT数量")
    recipient_address: str = Field(description="接收地址")
    network: str = Field(description="网络类型 (trc20/erc20)", default="trc20")


class TransactionResult(BaseModel):
    """交易结果"""
    success: bool
    transaction_id: Optional[str] = None
    amount: Optional[float] = None
    network: Optional[str] = None
    error: Optional[str] = None


@mcp.tool()
async def send_usdt(params: SendCryptoParams, ctx: Context) -> TransactionResult:
    """发送USDT到指定地址
    
    向指定的加密货币地址发送USDT代币
    """
    try:
        await ctx.info(f"发送USDT: {params.amount} 到 {params.recipient_address}")
        
        # 验证网络类型
        network = NetworkType(params.network.lower())
        
        # 检查余额
        balance_amount = await coinremitter_service.get_balance_amount(network)
        if balance_amount < params.amount:
            raise ValueError(f"余额不足: 需要 {params.amount}, 当前 {balance_amount}")
        
        # 执行提现
        transaction = await coinremitter_service.withdraw(
            amount=params.amount,
            address=params.recipient_address,
            network=network
        )
        
        await ctx.info(f"发送成功: {transaction.transaction_id}")
        
        return TransactionResult(
            success=True,
            transaction_id=transaction.transaction_id,
            amount=params.amount,
            network=params.network
        )
        
    except Exception as e:
        error_msg = f"发送USDT失败: {str(e)}"
        await ctx.error(error_msg)
        return TransactionResult(success=False, error=error_msg)


class BalanceResult(BaseModel):
    """余额结果"""
    success: bool
    balance: Optional[float] = None
    network: Optional[str] = None
    error: Optional[str] = None


@mcp.tool()
async def check_balance(network: str, ctx: Context) -> BalanceResult:
    """检查钱包余额
    
    查询指定网络的USDT余额
    """
    try:
        await ctx.info(f"查询{network}余额")
        
        # 验证网络类型
        network_type = NetworkType(network.lower())
        
        # 获取余额
        balance = await coinremitter_service.get_balance(network_type)
        
        await ctx.info(f"{network}余额: {balance.balance} USDT")
        
        return BalanceResult(
            success=True,
            balance=balance.balance,
            network=network
        )
        
    except Exception as e:
        error_msg = f"查询余额失败: {str(e)}"
        await ctx.error(error_msg)
        return BalanceResult(success=False, error=error_msg)


class PriceResult(BaseModel):
    """价格结果"""
    success: bool
    price: Optional[float] = None
    symbol: Optional[str] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None


@mcp.tool()
async def get_usdt_price(ctx: Context) -> PriceResult:
    """获取USDT当前价格
    
    从DIA Oracle获取USDT的实时价格数据
    """
    try:
        await ctx.info("获取USDT价格")
        
        # 获取价格数据
        price_data = await dia_oracle_service.get_usdt_price()
        
        await ctx.info(f"USDT价格: ${price_data.price}")
        
        return PriceResult(
            success=True,
            price=price_data.price,
            symbol=price_data.symbol,
            timestamp=price_data.timestamp
        )
        
    except Exception as e:
        error_msg = f"获取价格失败: {str(e)}"
        await ctx.error(error_msg)
        return PriceResult(success=False, error=error_msg)


# ==================== MCP Resources ====================

@mcp.resource("payment://invoice/{invoice_id}")
async def get_payment_status(invoice_id: str) -> str:
    """获取支付发票状态
    
    查询指定发票ID的支付状态和详细信息
    """
    try:
        logger.debug(f"查询发票状态: {invoice_id}")
        
        # 这里应该调用Coinremitter API查询发票状态
        # 目前返回模拟数据
        payment_info = {
            "invoice_id": invoice_id,
            "status": "pending",
            "amount": 100.0,
            "network": "trc20",
            "created_at": "2025-07-15T12:00:00Z"
        }
        
        return f"""# 支付发票状态

**发票ID**: {payment_info['invoice_id']}
**状态**: {payment_info['status']}
**金额**: {payment_info['amount']} USDT
**网络**: {payment_info['network']}
**创建时间**: {payment_info['created_at']}
"""
        
    except Exception as e:
        logger.error(f"查询发票状态失败: {str(e)}")
        return f"错误: {str(e)}"


@mcp.resource("market://usdt/info")
async def get_market_info() -> str:
    """获取USDT市场信息
    
    提供USDT的当前市场数据和统计信息
    """
    try:
        logger.debug("获取USDT市场信息")
        
        # 获取价格数据
        price_data = await dia_oracle_service.get_usdt_price()
        
        return f"""# USDT 市场信息

## 基本信息
- **代币名称**: Tether USD
- **符号**: USDT
- **当前价格**: ${price_data.price:.4f}
- **更新时间**: {price_data.timestamp}

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
        logger.error(f"获取市场信息失败: {str(e)}")
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
- **平均确认时间**: 3-5分钟
- **手续费**: 根据网络拥堵情况变化

## 使用建议
- 小额支付: 推荐使用TRC20
- 大额支付: 推荐使用ERC20
- DeFi应用: 使用ERC20
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


# ==================== 运行服务器 ====================

def main():
    """MCP服务器入口点"""
    logger.info("启动FinAgent MCP服务器...")
    mcp.run()


if __name__ == "__main__":
    main() 