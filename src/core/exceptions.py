"""自定义异常模块
定义MCP系统中使用的各种异常类
"""

from typing import Any, Dict, Optional


class MCPBaseException(Exception):
    """MCP基础异常类"""
    
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None) -> None:
        self.message = message
        self.details = details or {}
        super().__init__(self.message)


class PaymentException(MCPBaseException):
    """支付相关异常"""
    pass


class NetworkException(MCPBaseException):
    """网络请求异常"""
    pass


class ValidationException(MCPBaseException):
    """数据验证异常"""
    pass


class ConfigurationException(MCPBaseException):
    """配置异常"""
    pass


class AgentException(MCPBaseException):
    """Agent相关异常"""
    pass


class CoinremitterException(PaymentException):
    """Coinremitter API异常"""
    pass


class DIAOracleException(NetworkException):
    """DIA Oracle API异常"""
    pass


class WebhookException(MCPBaseException):
    """Webhook处理异常"""
    pass


class InsufficientFundsException(PaymentException):
    """余额不足异常"""
    pass


class InvalidAmountException(ValidationException):
    """无效金额异常"""
    pass


class UnsupportedNetworkException(ValidationException):
    """不支持的网络类型异常"""
    pass


class ExpiredInvoiceException(PaymentException):
    """发票过期异常"""
    pass 