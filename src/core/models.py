"""数据模型模块
定义API请求和响应的Pydantic模型
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, validator


class NetworkType(str, Enum):
    """网络类型枚举"""
    TRC20 = "trc20"
    ERC20 = "erc20"


class PaymentStatus(str, Enum):
    """支付状态枚举"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    EXPIRED = "expired"
    CANCELLED = "cancelled"


class CreatePaymentRequest(BaseModel):
    """创建支付请求模型"""
    amount_usd: float = Field(..., gt=0, description="USD金额")
    network: NetworkType = Field(default=NetworkType.TRC20, description="网络类型")
    callback_url: Optional[str] = Field(None, description="回调URL")
    
    @validator('callback_url')
    def validate_callback_url(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        
        # 使用安全模块验证URL格式
        from .security import security_validator
        if not security_validator.validate_url(v):
            raise ValueError("无效的回调URL格式")
        
        return v
    description: Optional[str] = Field(None, max_length=200, description="支付描述")
    
    @validator('description')
    def validate_description(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        
        # 使用安全模块清理输入
        from .security import security_validator
        return security_validator.sanitize_input(v, max_length=200)
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")
    
    @validator('amount_usd')
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("金额必须大于0")
        return v


class PaymentResponse(BaseModel):
    """支付响应模型"""
    invoice_id: str = Field(..., description="发票ID")
    payment_address: str = Field(..., description="支付地址")
    amount_usdt: float = Field(..., description="USDT金额")
    amount_usd: float = Field(..., description="USD金额")
    network: NetworkType = Field(..., description="网络类型")
    status: PaymentStatus = Field(..., description="支付状态")
    expires_at: datetime = Field(..., description="过期时间")
    qr_code_url: Optional[str] = Field(None, description="二维码URL")
    payment_url: Optional[str] = Field(None, description="支付URL")


class WebhookPayload(BaseModel):
    """Webhook负载模型"""
    invoice_id: str = Field(..., description="发票ID")
    status: PaymentStatus = Field(..., description="支付状态")
    amount_usdt: float = Field(..., description="USDT金额")
    network: NetworkType = Field(..., description="网络类型")
    transaction_hash: Optional[str] = Field(None, description="交易哈希")
    confirmations: int = Field(default=0, description="确认数")
    timestamp: datetime = Field(..., description="时间戳")
    metadata: Optional[Dict[str, Any]] = Field(default_factory=dict, description="元数据")


class SendStablecoinRequest(BaseModel):
    """发送稳定币请求模型"""
    recipient: str = Field(..., description="接收地址")
    amount: float = Field(..., gt=0, description="发送金额(USDT)")
    network: NetworkType = Field(default=NetworkType.TRC20, description="网络类型")
    
    @validator('amount')
    def validate_amount(cls, v: float) -> float:
        if v <= 0:
            raise ValueError("金额必须大于0")
        return v
    
    @validator('recipient')
    def validate_recipient(cls, v: str, values) -> str:
        if not v or len(v.strip()) == 0:
            raise ValueError("接收地址不能为空")
        
        # 使用安全模块验证地址格式
        from .security import security_validator
        network = values.get('network', 'trc20')
        if not security_validator.validate_crypto_address(v.strip(), network.value):
            raise ValueError(f"无效的{network.value.upper()}地址格式")
        
        return v.strip()


class TransactionResponse(BaseModel):
    """交易响应模型"""
    transaction_id: str = Field(..., description="交易ID")
    transaction_hash: Optional[str] = Field(None, description="交易哈希")
    status: str = Field(..., description="交易状态")
    amount: float = Field(..., description="交易金额")
    network: NetworkType = Field(..., description="网络类型")
    recipient: str = Field(..., description="接收地址")
    created_at: datetime = Field(..., description="创建时间")


class BalanceResponse(BaseModel):
    """余额响应模型"""
    balance: Optional[float] = Field(None, description="单个网络余额")
    network: Optional[NetworkType] = Field(None, description="网络类型")
    trc20_balance: Optional[float] = Field(None, description="TRC20 USDT余额")
    erc20_balance: Optional[float] = Field(None, description="ERC20 USDT余额")
    total_balance: Optional[float] = Field(None, description="总余额")
    updated_at: datetime = Field(..., description="更新时间")


class PriceResponse(BaseModel):
    """价格响应模型"""
    symbol: str = Field(..., description="代币符号")
    price_usd: float = Field(..., description="USD价格")
    timestamp: datetime = Field(..., description="价格时间戳")
    source: str = Field(..., description="价格来源")


class ErrorResponse(BaseModel):
    """错误响应模型"""
    error: str = Field(..., description="错误类型")
    message: str = Field(..., description="错误消息")
    details: Optional[Dict[str, Any]] = Field(default_factory=dict, description="错误详情")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="错误时间")


class AgentMessage(BaseModel):
    """Agent消息模型"""
    type: str = Field(..., description="消息类型")
    sender: str = Field(..., description="发送者")
    recipient: str = Field(..., description="接收者")
    payload: Dict[str, Any] = Field(..., description="消息负载")
    timestamp: datetime = Field(default_factory=datetime.utcnow, description="发送时间")


class InvoiceStatus(BaseModel):
    """发票状态模型"""
    invoice_id: str = Field(..., description="发票ID")
    status: PaymentStatus = Field(..., description="支付状态")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    expires_at: datetime = Field(..., description="过期时间")
    amount_usdt: float = Field(..., description="USDT金额")
    amount_paid: float = Field(default=0.0, description="已支付金额")
    network: NetworkType = Field(..., description="网络类型")
    payment_address: str = Field(..., description="支付地址")
    transaction_hash: Optional[str] = Field(None, description="交易哈希")
    confirmations: int = Field(default=0, description="确认数") 