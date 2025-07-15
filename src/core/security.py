"""安全性模块
包含输入验证、密钥生成、安全检查等功能
"""

import re
import secrets
import hashlib
from typing import Any, Dict, List, Optional, Union
from urllib.parse import urlparse

from loguru import logger


class SecurityValidator:
    """安全验证器"""
    
    # 地址格式正则表达式
    TRC20_ADDRESS_PATTERN = re.compile(r'^T[A-Za-z1-9]{33}$')
    ERC20_ADDRESS_PATTERN = re.compile(r'^0x[a-fA-F0-9]{40}$')
    
    # 危险字符模式
    DANGEROUS_PATTERNS = [
        r'[<>"\']',  # XSS相关字符
        r'(union|select|insert|update|delete|drop|create|alter)',  # SQL注入
        r'(script|javascript|vbscript)',  # 脚本注入
        r'(eval|exec|system|shell)',  # 代码执行
    ]
    
    @classmethod
    def validate_crypto_address(cls, address: str, network: str) -> bool:
        """验证加密货币地址格式
        
        Args:
            address: 地址字符串
            network: 网络类型 (trc20/erc20)
            
        Returns:
            bool: 地址是否有效
        """
        if not address or not isinstance(address, str):
            return False
            
        network = network.lower()
        if network == "trc20":
            return bool(cls.TRC20_ADDRESS_PATTERN.match(address))
        elif network == "erc20":
            return bool(cls.ERC20_ADDRESS_PATTERN.match(address))
        else:
            return False
    
    @classmethod
    def validate_amount(cls, amount: Union[int, float], min_amount: float = 0.1, max_amount: float = 10000.0) -> bool:
        """验证金额范围
        
        Args:
            amount: 金额
            min_amount: 最小金额
            max_amount: 最大金额
            
        Returns:
            bool: 金额是否有效
        """
        if not isinstance(amount, (int, float)):
            return False
            
        return min_amount <= amount <= max_amount and amount > 0
    
    @classmethod
    def sanitize_input(cls, input_str: str, max_length: int = 200) -> str:
        """清理输入字符串
        
        Args:
            input_str: 输入字符串
            max_length: 最大长度
            
        Returns:
            str: 清理后的字符串
        """
        if not isinstance(input_str, str):
            return ""
            
        # 限制长度
        cleaned = input_str[:max_length]
        
        # 检查危险模式
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, cleaned, re.IGNORECASE):
                logger.warning(f"检测到潜在危险输入: {pattern}")
                # 移除危险字符
                cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE)
        
        return cleaned.strip()
    
    @classmethod
    def validate_url(cls, url: str) -> bool:
        """验证URL格式
        
        Args:
            url: URL字符串
            
        Returns:
            bool: URL是否有效
        """
        try:
            result = urlparse(url)
            return all([result.scheme, result.netloc]) and result.scheme in ['http', 'https']
        except Exception:
            return False
    
    @classmethod
    def mask_sensitive_data(cls, data: str, mask_char: str = "*", visible_chars: int = 4) -> str:
        """屏蔽敏感数据
        
        Args:
            data: 敏感数据字符串
            mask_char: 屏蔽字符
            visible_chars: 可见字符数
            
        Returns:
            str: 屏蔽后的字符串
        """
        if not data or len(data) <= visible_chars:
            return mask_char * 8  # 返回固定长度的屏蔽字符
            
        visible_start = data[:visible_chars]
        masked_middle = mask_char * (len(data) - visible_chars)
        
        return f"{visible_start}{masked_middle}"


class SecureKeyGenerator:
    """安全密钥生成器"""
    
    @staticmethod
    def generate_api_key(prefix: str = "fa", length: int = 32) -> str:
        """生成API密钥
        
        Args:
            prefix: 密钥前缀
            length: 随机部分长度
            
        Returns:
            str: 生成的API密钥
        """
        random_part = secrets.token_urlsafe(length)
        return f"{prefix}_{random_part}"
    
    @staticmethod
    def generate_webhook_secret(length: int = 32) -> str:
        """生成Webhook密钥
        
        Args:
            length: 密钥长度
            
        Returns:
            str: 生成的Webhook密钥
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_hmac_secret(length: int = 32) -> str:
        """生成HMAC密钥
        
        Args:
            length: 密钥长度
            
        Returns:
            str: 生成的HMAC密钥
        """
        return secrets.token_urlsafe(length)
    
    @staticmethod
    def generate_jwt_secret(length: int = 32) -> str:
        """生成JWT密钥
        
        Args:
            length: 密钥长度
            
        Returns:
            str: 生成的JWT密钥
        """
        return secrets.token_urlsafe(length)


class SecurityChecker:
    """安全检查器"""
    
    @staticmethod
    def check_environment_security() -> Dict[str, Any]:
        """检查环境安全配置
        
        Returns:
            Dict: 安全检查结果
        """
        issues = []
        warnings = []
        
        # 检查环境变量
        import os
        
        # 检查关键环境变量是否设置
        required_vars = [
            "COINREMITTER_TRC20_API_KEY",
            "COINREMITTER_ERC20_API_KEY",
            "HMAC_SECRET",
            "JWT_SECRET"
        ]
        
        for var in required_vars:
            value = os.getenv(var)
            if not value:
                issues.append(f"缺少环境变量: {var}")
            elif len(value) < 16:
                warnings.append(f"环境变量 {var} 长度可能不够安全")
        
        # 检查DEBUG模式
        debug = os.getenv("DEBUG", "false").lower()
        if debug == "true":
            warnings.append("DEBUG模式已启用，生产环境应禁用")
        
        # 检查CORS配置
        cors_origins = os.getenv("CORS_ORIGINS", "*")
        if cors_origins == "*":
            warnings.append("CORS配置允许所有域名，生产环境应限制")
        
        return {
            "issues": issues,
            "warnings": warnings,
            "status": "safe" if not issues else "unsafe"
        }
    
    @staticmethod
    def validate_request_headers(headers: Dict[str, str]) -> bool:
        """验证请求头安全性
        
        Args:
            headers: 请求头字典
            
        Returns:
            bool: 请求头是否安全
        """
        # 检查User-Agent
        user_agent = headers.get("user-agent", "").lower()
        suspicious_agents = ["curl", "wget", "python-requests", "bot", "crawler"]
        
        if any(agent in user_agent for agent in suspicious_agents):
            logger.warning(f"检测到可疑User-Agent: {user_agent}")
            return False
        
        # 检查Content-Length
        content_length = headers.get("content-length")
        if content_length and int(content_length) > 1024 * 1024:  # 1MB限制
            logger.warning(f"请求体过大: {content_length} bytes")
            return False
        
        return True


# 全局安全验证器实例
security_validator = SecurityValidator()
secure_key_generator = SecureKeyGenerator()
security_checker = SecurityChecker() 