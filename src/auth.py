"""FinAgent MCP Server 身份验证模块
支持Bearer Token、API Key等多种认证方式
"""

import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass

import jwt
from loguru import logger


@dataclass 
class AuthConfig:
    """认证配置"""
    # 基础认证
    auth_token: Optional[str] = os.getenv("AUTH_TOKEN")
    api_key: Optional[str] = os.getenv("API_KEY")
    
    # JWT配置
    jwt_secret: str = os.getenv("JWT_SECRET") or secrets.token_urlsafe(32)
    jwt_algorithm: str = "HS256"
    jwt_expiration_hours: int = 24
    
    # HMAC配置
    hmac_secret: str = os.getenv("HMAC_SECRET") or secrets.token_urlsafe(32)
    
    # 令牌生成
    token_length: int = 32


auth_config = AuthConfig()


class AuthenticationError(Exception):
    """认证错误"""
    pass


class AuthManager:
    """认证管理器"""
    
    def __init__(self, config: AuthConfig = None):
        self.config = config or auth_config
        
    def generate_token(self, length: int = None) -> str:
        """生成安全令牌"""
        length = length or self.config.token_length
        return secrets.token_urlsafe(length)
    
    def generate_api_key(self, prefix: str = "fa") -> str:
        """生成API密钥"""
        random_part = secrets.token_urlsafe(24)
        return f"{prefix}_{random_part}"
    
    def verify_bearer_token(self, token: str) -> bool:
        """验证Bearer Token"""
        if not self.config.auth_token:
            return True  # 未配置认证时允许访问
        
        return hmac.compare_digest(token, self.config.auth_token)
    
    def verify_api_key(self, api_key: str) -> bool:
        """验证API Key"""
        if not self.config.api_key:
            return True  # 未配置API Key时允许访问
            
        return hmac.compare_digest(api_key, self.config.api_key)
    
    def create_jwt_token(self, payload: Dict[str, Any]) -> str:
        """创建JWT令牌"""
        # 添加标准声明
        now = datetime.now(timezone.utc)
        payload.update({
            "iat": now,  # 签发时间
            "exp": now + timedelta(hours=self.config.jwt_expiration_hours),  # 过期时间
            "iss": "finagent-mcp-server",  # 签发者
        })
        
        return jwt.encode(
            payload, 
            self.config.jwt_secret, 
            algorithm=self.config.jwt_algorithm
        )
    
    def verify_jwt_token(self, token: str) -> Tuple[bool, Optional[Dict[str, Any]]]:
        """验证JWT令牌"""
        try:
            payload = jwt.decode(
                token, 
                self.config.jwt_secret, 
                algorithms=[self.config.jwt_algorithm]
            )
            return True, payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token已过期")
            return False, None
        except jwt.InvalidTokenError as e:
            logger.warning(f"JWT token无效: {e}")
            return False, None
    
    def create_hmac_signature(self, data: str, timestamp: str = None) -> str:
        """创建HMAC签名"""
        timestamp = timestamp or str(int(datetime.now().timestamp()))
        message = f"{timestamp}.{data}"
        
        signature = hmac.new(
            self.config.hmac_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()
        
        return f"t={timestamp},v1={signature}"
    
    def verify_hmac_signature(self, data: str, signature: str, tolerance: int = 300) -> bool:
        """验证HMAC签名"""
        try:
            # 解析签名
            parts = {}
            for part in signature.split(","):
                key, value = part.split("=", 1)
                parts[key] = value
            
            timestamp = int(parts.get("t", "0"))
            received_signature = parts.get("v1", "")
            
            # 检查时间戳
            current_time = int(datetime.now().timestamp())
            if abs(current_time - timestamp) > tolerance:
                logger.warning("HMAC签名时间戳超出容忍范围")
                return False
            
            # 重新计算签名
            message = f"{timestamp}.{data}"
            expected_signature = hmac.new(
                self.config.hmac_secret.encode(),
                message.encode(),
                hashlib.sha256
            ).hexdigest()
            
            # 比较签名
            return hmac.compare_digest(received_signature, expected_signature)
            
        except (ValueError, KeyError) as e:
            logger.warning(f"HMAC签名格式错误: {e}")
            return False
    
    def authenticate_request(self, headers: Dict[str, str]) -> Tuple[bool, Optional[str]]:
        """验证请求认证
        
        Args:
            headers: HTTP请求头
            
        Returns:
            Tuple[bool, Optional[str]]: (是否通过认证, 错误信息)
        """
        # 如果没有配置任何认证，允许访问
        if not any([
            self.config.auth_token,
            self.config.api_key
        ]):
            return True, None
        
        # 检查Authorization头
        auth_header = headers.get("authorization", "").strip()
        if auth_header:
            # Bearer Token认证
            if auth_header.startswith("Bearer "):
                token = auth_header[7:]
                if self.verify_bearer_token(token):
                    return True, None
                else:
                    return False, "Invalid Bearer token"
            
            # Basic认证（暂不实现）
            elif auth_header.startswith("Basic "):
                return False, "Basic authentication not supported"
        
        # 检查API Key头
        api_key = headers.get("x-api-key", "") or headers.get("api-key", "")
        if api_key:
            if self.verify_api_key(api_key):
                return True, None
            else:
                return False, "Invalid API key"
        
        # 检查JWT Token
        jwt_token = headers.get("x-jwt-token", "")
        if jwt_token:
            valid, payload = self.verify_jwt_token(jwt_token)
            if valid:
                return True, None
            else:
                return False, "Invalid JWT token"
        
        # 如果配置了认证但没有提供有效凭据
        return False, "Authentication required"


# 全局认证管理器实例
auth_manager = AuthManager()


def generate_client_config(auth_token: str = None) -> Dict[str, Any]:
    """生成客户端配置
    
    Args:
        auth_token: 认证令牌
        
    Returns:
        Dict: 客户端配置
    """
    config = {
        "mcpServers": {
            "finagent-cloud": {
                "url": "https://your-server-url.com/mcp",
                "transport": "streamable-http",
                "description": "FinAgent云端MCP服务器"
            }
        }
    }
    
    # 添加认证配置
    if auth_token:
        config["mcpServers"]["finagent-cloud"]["auth"] = {
            "type": "bearer",
            "token": auth_token
        }
    
    return config


def create_auth_headers(auth_token: str = None, api_key: str = None) -> Dict[str, str]:
    """创建认证请求头
    
    Args:
        auth_token: Bearer Token
        api_key: API Key
        
    Returns:
        Dict: HTTP请求头
    """
    headers = {}
    
    if auth_token:
        headers["Authorization"] = f"Bearer {auth_token}"
    
    if api_key:
        headers["X-API-Key"] = api_key
    
    return headers


# 认证装饰器
def require_auth(func):
    """认证装饰器"""
    def wrapper(*args, **kwargs):
        # 这里可以添加认证逻辑
        # 对于MCP服务器，认证通常在传输层处理
        return func(*args, **kwargs)
    return wrapper 