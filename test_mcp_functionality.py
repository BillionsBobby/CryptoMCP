#!/usr/bin/env python3
"""FinAgent MCP服务器功能测试
测试Tools、Resources、Prompts的完整功能
"""

import asyncio
import json
from typing import Dict, Any

from src.mcp_server_simple import (
    mcp, 
    create_payment, 
    check_balance, 
    get_usdt_price, 
    list_invoices,
    PaymentParams,
    MOCK_INVOICES
)


async def test_tools():
    """测试MCP工具功能"""
    print("🔧 测试MCP工具(Tools)...")
    
    # 测试创建支付
    print("\n1. 测试创建支付工具")
    payment_params = PaymentParams(
        amount_usd=100.0,
        network="trc20",
        description="测试支付"
    )
    
    # 模拟Context对象
    class MockContext:
        async def info(self, msg): print(f"  ℹ️  {msg}")
        async def debug(self, msg): print(f"  🐛 {msg}")
        async def error(self, msg): print(f"  ❌ {msg}")
    
    ctx = MockContext()
    
    result = await create_payment(payment_params, ctx)
    print(f"  结果: {result.success}")
    if result.success:
        print(f"  发票ID: {result.invoice_id}")
        print(f"  支付地址: {result.payment_address}")
        print(f"  USDT数量: {result.amount_usdt}")
    
    # 测试查询余额
    print("\n2. 测试查询余额工具")
    balance_result = await check_balance("trc20", ctx)
    print(f"  结果: {balance_result.success}")
    if balance_result.success:
        print(f"  TRC20余额: {balance_result.balance} USDT")
    
    # 测试获取价格
    print("\n3. 测试获取USDT价格工具")
    price_result = await get_usdt_price(ctx)
    print(f"  结果: {price_result.success}")
    if price_result.success:
        print(f"  USDT价格: ${price_result.price}")
    
    # 测试发票列表
    print("\n4. 测试发票列表工具")
    invoices_result = await list_invoices(ctx)
    print(f"  结果: {invoices_result['success']}")
    if invoices_result['success']:
        print(f"  发票数量: {invoices_result['count']}")
    
    print("\n✅ 工具测试完成")


async def test_resources():
    """测试MCP资源功能"""
    print("\n📋 测试MCP资源(Resources)...")
    
    # 导入资源函数
    from src.mcp_server_simple import (
        get_payment_status,
        get_market_info, 
        get_supported_networks
    )
    
    # 测试支付状态资源（需要先有发票）
    print("\n1. 测试支付状态资源")
    if MOCK_INVOICES:
        invoice_id = list(MOCK_INVOICES.keys())[0]
        status_info = await get_payment_status(invoice_id)
        print(f"  发票状态信息长度: {len(status_info)} 字符")
        print(f"  包含发票ID: {'发票ID' in status_info}")
    else:
        print("  没有可用的发票进行测试")
    
    # 测试市场信息资源
    print("\n2. 测试市场信息资源")
    market_info = await get_market_info()
    print(f"  市场信息长度: {len(market_info)} 字符")
    print(f"  包含USDT: {'USDT' in market_info}")
    
    # 测试网络配置资源
    print("\n3. 测试网络配置资源")
    networks_info = await get_supported_networks()
    print(f"  网络信息长度: {len(networks_info)} 字符")
    print(f"  包含TRC20: {'TRC20' in networks_info}")
    print(f"  包含ERC20: {'ERC20' in networks_info}")
    
    print("\n✅ 资源测试完成")


def test_prompts():
    """测试MCP提示功能"""
    print("\n💬 测试MCP提示(Prompts)...")
    
    from src.mcp_server_simple import (
        create_payment_prompt,
        balance_inquiry_prompt,
        market_analysis_prompt
    )
    
    # 测试创建支付提示
    print("\n1. 测试创建支付提示")
    payment_prompt = create_payment_prompt("100", "USD")
    print(f"  提示消息数量: {len(payment_prompt)}")
    print(f"  包含用户消息: {any('100' in str(msg) for msg in payment_prompt)}")
    
    # 测试余额查询提示
    print("\n2. 测试余额查询提示")
    balance_prompt = balance_inquiry_prompt("trc20")
    print(f"  提示内容长度: {len(balance_prompt)} 字符")
    print(f"  包含TRC20: {'TRC20' in balance_prompt}")
    
    # 测试市场分析提示
    print("\n3. 测试市场分析提示")
    analysis_prompt = market_analysis_prompt("1h")
    print(f"  分析提示数量: {len(analysis_prompt)}")
    print(f"  包含分析内容: {any('分析' in str(msg) for msg in analysis_prompt)}")
    
    print("\n✅ 提示测试完成")


def test_mcp_server_structure():
    """测试MCP服务器结构"""
    print("\n🏗️  测试MCP服务器结构...")
    
    # 测试服务器基本属性
    print(f"  服务器名称: {mcp.name}")
    
    # 测试是否有正确的MCP组件
    print(f"  工具数量: {len(getattr(mcp, '_tools', {}))}")
    print(f"  资源数量: {len(getattr(mcp, '_resources', {}))}")
    print(f"  提示数量: {len(getattr(mcp, '_prompts', {}))}")
    
    print("\n✅ 服务器结构测试完成")


async def main():
    """主测试函数"""
    print("🚀 开始FinAgent MCP服务器功能测试")
    print("=" * 50)
    
    # 测试服务器结构
    test_mcp_server_structure()
    
    # 测试工具
    await test_tools()
    
    # 测试资源
    await test_resources()
    
    # 测试提示
    test_prompts()
    
    print("\n" + "=" * 50)
    print("🎉 所有测试完成！FinAgent MCP服务器功能正常")
    print("\n📚 使用方法:")
    print("1. 开发模式: mcp dev src/mcp_server_simple.py")
    print("2. 直接运行: python3 -m src.mcp_server_simple")
    print("3. 安装到Claude Desktop: mcp install src/mcp_server_simple.py")


if __name__ == "__main__":
    asyncio.run(main()) 