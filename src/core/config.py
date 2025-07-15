"""配置管理模块
使用Pydantic Settings管理环境变量和配置
"""

from typing import Optional
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """应用程序配置类"""
    
    # 应用基础配置
    app_name: str = Field(default="MCP Crypto Payment", description="应用名称")
    app_version: str = Field(default="0.1.0", description="应用版本")
    debug: bool = Field(default=False, description="调试模式")
    
    # API服务配置
    host: str = Field(default="0.0.0.0", description="服务器主机")
    port: int = Field(default=8000, description="服务器端口")
    
    # Coinremitter API配置 - TRC20
    coinremitter_trc20_api_key: str = Field(default="", description="Coinremitter TRC20 API密钥")
    coinremitter_trc20_password: str = Field(default="", description="Coinremitter TRC20 密码")
    coinremitter_trc20_webhook_secret: str = Field(default="", description="Coinremitter TRC20 Webhook密钥")
    
    # Coinremitter API配置 - ERC20
    coinremitter_erc20_api_key: str = Field(default="", description="Coinremitter ERC20 API密钥")
    coinremitter_erc20_password: str = Field(default="", description="Coinremitter ERC20 密码")
    coinremitter_erc20_webhook_secret: str = Field(default="", description="Coinremitter ERC20 Webhook密钥")
    
    # DIA Oracle配置
    dia_oracle_base_url: str = Field(
        default="https://api.diadata.org/v1/assetQuotation/Ethereum/0xdAC17F958D2ee523a2206206994597C13D831ec7",
        description="DIA Oracle API基础URL"
    )
    
    # uAgents配置
    agent_name: str = Field(default="mcp_payment_agent", description="代理名称")
    agent_seed: Optional[str] = Field(default=None, description="代理种子")
    agent_port: int = Field(default=8001, description="代理端口")
    
    # 支付配置
    default_network: str = Field(default="trc20", description="默认网络(trc20/erc20)")
    min_payment_amount: float = Field(default=0.1, description="最小支付金额(USDT)")
    max_payment_amount: float = Field(default=10000.0, description="最大支付金额(USDT)")
    payment_timeout: int = Field(default=3600, description="支付超时时间(秒)")
    
    # 安全配置
    hmac_secret: str = Field(default="", description="HMAC签名密钥")
    jwt_secret: str = Field(default="", description="JWT密钥")
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False


# 全局配置实例
settings = Settings() 