#!/usr/bin/env python3
"""FinAgent MCP Server CLI
命令行接口，支持多种传输方式
"""

import argparse
import asyncio
import sys
from pathlib import Path

from loguru import logger

# 添加项目根目录到Python路径
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from src.mcp_server import mcp
from src.core.utils import setup_logger


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="FinAgent MCP Server - AI Agent的加密货币支付服务"
    )
    parser.add_argument(
        "transport",
        choices=["stdio", "sse", "streamable-http"],
        default="stdio",
        nargs="?",
        help="传输方式 (默认: stdio)"
    )
    parser.add_argument(
        "--host",
        default="localhost",
        help="服务器主机 (仅用于sse/streamable-http)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="服务器端口 (仅用于sse/streamable-http)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="启用调试模式"
    )
    
    args = parser.parse_args()
    
    # 设置日志
    setup_logger()
    
    if args.debug:
        logger.info("调试模式已启用")
    
    try:
        logger.info(f"🚀 启动FinAgent MCP服务器 (传输方式: {args.transport})")
        
        if args.transport == "stdio":
            # 标准输入输出模式
            mcp.run(transport="stdio")
        elif args.transport == "sse":
            # Server-Sent Events模式
            mcp.run(transport="sse", host=args.host, port=args.port)
        elif args.transport == "streamable-http":
            # Streamable HTTP模式
            mcp.run(transport="streamable-http", host=args.host, port=args.port)
        else:
            logger.error(f"不支持的传输方式: {args.transport}")
            sys.exit(1)
            
    except KeyboardInterrupt:
        logger.info("👋 服务器已停止")
    except Exception as e:
        logger.error(f"❌ 服务器错误: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 