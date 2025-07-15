#!/usr/bin/env python3
"""FinAgent 简化 MCP Server
用于测试的简化版本，不依赖外部API
"""

import asyncio
import os
import json
from datetime import datetime
from typing import List, Optional

from mcp.server.fastmcp import FastMCP, Context
from mcp.server.fastmcp.prompts import base
from pydantic import BaseModel, Field
from loguru import logger


# 创建FastMCP服务器
mcp = FastMCP(
    name="FinAgent-Simple",
    description="FinAgent简化版MCP服务器 - 加密货币支付和市场数据"
)


# ==================== 数据模型 ====================

class PaymentParams(BaseModel):
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


class BalanceResult(BaseModel):
    """余额结果"""
    success: bool
    balance: Optional[float] = None
    network: Optional[str] = None
    error: Optional[str] = None


class PriceResult(BaseModel):
    """价格结果"""
    success: bool
    price: Optional[float] = None
    symbol: Optional[str] = None
    timestamp: Optional[str] = None
    error: Optional[str] = None


# ==================== 模拟数据 ====================

# 模拟账户余额
MOCK_BALANCES = {
    "trc20": 1000.0,
    "erc20": 500.0
}

# 模拟USDT价格（通常接近1美元）
MOCK_USDT_PRICE = 0.9998

# 模拟支付发票存储
MOCK_INVOICES = {}


def generate_mock_address(network: str) -> str:
    """生成模拟地址"""
    if network.lower() == "trc20":
        return f"TR{hash(datetime.now()) % 1000000:06d}{'x' * 28}"
    else:  # erc20
        return f"0x{hash(datetime.now()) % 10**40:040x}"


def generate_invoice_id() -> str:
    """生成发票ID"""
    return f"INV_{datetime.now().strftime('%Y%m%d%H%M%S')}_{hash(datetime.now()) % 10000:04d}"


# ==================== MCP Tools ====================

@mcp.tool()
async def create_payment(params: PaymentParams, ctx: Context) -> PaymentResult:
    """创建USDT支付发票
    
    根据USD金额创建加密货币支付发票，支持TRC20和ERC20网络
    """
    try:
        await ctx.info(f"创建支付: ${params.amount_usd} USD, 网络: {params.network}")
        
        # 验证参数
        if params.amount_usd <= 0:
            raise ValueError("金额必须大于0")
        
        if params.network.lower() not in ["trc20", "erc20"]:
            raise ValueError("网络类型必须是trc20或erc20")
        
        # 计算USDT数量（使用模拟价格）
        usdt_amount = params.amount_usd / MOCK_USDT_PRICE
        await ctx.debug(f"计算得出USDT数量: {usdt_amount}")
        
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
        
        await ctx.info(f"支付发票创建成功: {invoice_id}")
        
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
        await ctx.error(error_msg)
        return PaymentResult(success=False, error=error_msg)


@mcp.tool()
async def check_balance(network: str, ctx: Context) -> BalanceResult:
    """检查钱包余额
    
    查询指定网络的USDT余额
    """
    try:
        await ctx.info(f"查询{network}余额")
        
        # 验证网络类型
        if network.lower() not in ["trc20", "erc20"]:
            raise ValueError("网络类型必须是trc20或erc20")
        
        # 获取模拟余额
        balance = MOCK_BALANCES.get(network.lower(), 0.0)
        
        await ctx.info(f"{network}余额: {balance} USDT")
        
        return BalanceResult(
            success=True,
            balance=balance,
            network=network
        )
        
    except Exception as e:
        error_msg = f"查询余额失败: {str(e)}"
        await ctx.error(error_msg)
        return BalanceResult(success=False, error=error_msg)


@mcp.tool()
async def get_usdt_price(ctx: Context) -> PriceResult:
    """获取USDT当前价格
    
    获取USDT的实时价格数据（模拟数据）
    """
    try:
        await ctx.info("获取USDT价格")
        
        # 返回模拟价格数据
        return PriceResult(
            success=True,
            price=MOCK_USDT_PRICE,
            symbol="USDT",
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        error_msg = f"获取价格失败: {str(e)}"
        await ctx.error(error_msg)
        return PriceResult(success=False, error=error_msg)


@mcp.tool()
async def list_invoices(ctx: Context) -> dict:
    """列出所有支付发票
    
    返回所有创建的支付发票列表
    """
    try:
        await ctx.info("获取发票列表")
        
        return {
            "success": True,
            "count": len(MOCK_INVOICES),
            "invoices": list(MOCK_INVOICES.values())
        }
        
    except Exception as e:
        error_msg = f"获取发票列表失败: {str(e)}"
        await ctx.error(error_msg)
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
**金额**: {invoice['amount_usdt']:.4f} USDT (${invoice['amount_usd']:.2f} USD)
**网络**: {invoice['network'].upper()}
**支付地址**: `{invoice['address']}`
**描述**: {invoice.get('description', '无')}
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
- **市值排名**: #3

## 网络支持
- **TRC20** (Tron): 低手续费，快速确认
- **ERC20** (Ethereum): 广泛支持，流动性高

## 当前余额
- **TRC20**: {MOCK_BALANCES['trc20']} USDT
- **ERC20**: {MOCK_BALANCES['erc20']} USDT

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
- **推荐用途**: 小额支付、频繁交易

## ERC20 (Ethereum)
- **网络名称**: Ethereum
- **代币标准**: ERC20
- **区块确认**: 12确认
- **平均确认时间**: 3-5分钟
- **手续费**: 根据网络拥堵情况变化
- **推荐用途**: 大额支付、DeFi应用

## 使用建议
- **小额支付** (< $100): 推荐使用TRC20
- **大额支付** (> $100): 推荐使用ERC20
- **DeFi应用**: 使用ERC20
- **跨链桥接**: 注意网络兼容性
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
        base.AssistantMessage("3. 提供网络选择建议"),
        base.UserMessage(f"请分析{timeframe}时间框架内的数据")
    ]


# ==================== 运行服务器 ====================

def main():
    """MCP服务器入口点"""
    logger.info("启动FinAgent简化版MCP服务器...")
    mcp.run()


if __name__ == "__main__":
    main() 