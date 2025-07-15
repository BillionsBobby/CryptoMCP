"""通用工具模块
包含日志配置、验证、加密等通用功能
"""

import hashlib
import hmac
import json
import secrets
from datetime import datetime, timezone
from typing import Any, Dict, Optional, Union

from loguru import logger

from .config import settings


def setup_logger() -> None:
    """配置日志系统"""
    logger.remove()  # 移除默认处理器
    
    # 添加控制台输出
    logger.add(
        sink=lambda msg: print(msg, end=""),
        level="DEBUG" if settings.debug else "INFO",
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
               "<level>{level: <8}</level> | "
               "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
               "<level>{message}</level>",
        colorize=True,
    )
    
    # 添加文件输出
    logger.add(
        "logs/mcp_payment.log",
        rotation="1 day",
        retention="30 days",
        level="INFO",
        format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    )


def generate_secure_token(length: int = 32) -> str:
    """生成安全随机令牌"""
    return secrets.token_urlsafe(length)


def verify_hmac_signature(
    payload: Union[str, bytes], 
    signature: str, 
    secret: str,
    algorithm: str = "sha256"
) -> bool:
    """验证HMAC签名
    
    Args:
        payload: 要验证的数据
        signature: 接收到的签名
        secret: HMAC密钥
        algorithm: 哈希算法
        
    Returns:
        bool: 签名是否有效
    """
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    
    expected_signature = hmac.new(
        secret.encode('utf-8'),
        payload,
        getattr(hashlib, algorithm)
    ).hexdigest()
    
    return hmac.compare_digest(signature, expected_signature)


def create_hmac_signature(
    payload: Union[str, bytes], 
    secret: str,
    algorithm: str = "sha256"
) -> str:
    """创建HMAC签名
    
    Args:
        payload: 要签名的数据
        secret: HMAC密钥
        algorithm: 哈希算法
        
    Returns:
        str: 生成的签名
    """
    if isinstance(payload, str):
        payload = payload.encode('utf-8')
    
    return hmac.new(
        secret.encode('utf-8'),
        payload,
        getattr(hashlib, algorithm)
    ).hexdigest()


def validate_usdt_amount(amount: float) -> bool:
    """验证USDT金额是否有效
    
    Args:
        amount: USDT金额
        
    Returns:
        bool: 金额是否有效
    """
    return (
        isinstance(amount, (int, float)) and
        settings.min_payment_amount <= amount <= settings.max_payment_amount and
        amount > 0
    )


def format_usdt_amount(amount: float, decimals: int = 6) -> str:
    """格式化USDT金额
    
    Args:
        amount: USDT金额
        decimals: 小数位数
        
    Returns:
        str: 格式化后的金额字符串
    """
    return f"{amount:.{decimals}f}"


def get_current_timestamp() -> int:
    """获取当前UTC时间戳"""
    return int(datetime.now(timezone.utc).timestamp())


def safe_json_loads(data: str) -> Optional[Dict[str, Any]]:
    """安全的JSON解析
    
    Args:
        data: JSON字符串
        
    Returns:
        Optional[Dict]: 解析后的字典，失败时返回None
    """
    try:
        return json.loads(data)
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"JSON解析失败: {e}")
        return None


def validate_network_type(network: str) -> bool:
    """验证网络类型是否支持
    
    Args:
        network: 网络类型
        
    Returns:
        bool: 是否支持该网络
    """
    return network.lower() in ["trc20", "erc20"]


def generate_invoice_id() -> str:
    """生成发票ID"""
    timestamp = get_current_timestamp()
    random_str = generate_secure_token(8)
    return f"INV_{timestamp}_{random_str}"


# 初始化日志系统
setup_logger() 