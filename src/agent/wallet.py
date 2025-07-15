"""钱包Agent模块
基于uAgents框架实现的支付代理
"""

import asyncio
from datetime import datetime
from typing import Dict, Any, Optional

from uagents import Agent, Context, Model
from uagents.setup import fund_agent_if_low
from loguru import logger

from ..core.config import settings
from ..core.models import NetworkType, SendStablecoinRequest, TransactionResponse
from ..core.exceptions import AgentException, InsufficientFundsException
from ..services.coinremitter import coinremitter_service


class PaymentRequest(Model):
    """支付请求消息模型"""
    recipient: str
    amount: float
    network: str
    request_id: str


class PaymentResponse(Model):
    """支付响应消息模型"""
    request_id: str
    success: bool
    transaction_id: Optional[str] = None
    error_message: Optional[str] = None


class BalanceRequest(Model):
    """余额查询请求模型"""
    network: Optional[str] = None


# 使用核心模块的BalanceResponse
from ..core.models import BalanceResponse as CoreBalanceResponse


class WalletAgent:
    """钱包Agent类"""
    
    def __init__(self) -> None:
        """初始化钱包Agent"""
        self.agent = Agent(
            name=settings.agent_name,
            seed=settings.agent_seed,
            port=settings.agent_port,
            endpoint=[f"http://127.0.0.1:{settings.agent_port}/submit"],
        )
        
        # 注册消息处理器
        self._register_handlers()
        
        logger.info(f"钱包Agent初始化完成: {self.agent.name}")
        logger.info(f"Agent地址: {self.agent.address}")
    
    def _register_handlers(self) -> None:
        """注册消息处理器"""
        
        @self.agent.on_message(model=PaymentRequest)
        async def handle_payment_request(ctx: Context, sender: str, msg: PaymentRequest) -> None:
            """处理支付请求"""
            logger.info(f"收到支付请求: {msg.request_id} from {sender}")
            
            try:
                # 验证网络类型
                network = NetworkType(msg.network.lower())
                
                # 验证金额
                if msg.amount <= 0:
                    raise ValueError("支付金额必须大于0")
                
                # 检查余额
                balance_amount = await coinremitter_service.get_balance_amount(network)
                if balance_amount < msg.amount:
                    raise InsufficientFundsException(
                        f"余额不足: 需要 {msg.amount} USDT, 当前余额 {balance_amount} USDT"
                    )
                
                # 执行支付
                transaction = await coinremitter_service.withdraw(
                    amount=msg.amount,
                    address=msg.recipient,
                    network=network
                )
                
                # 发送成功响应
                response = PaymentResponse(
                    request_id=msg.request_id,
                    success=True,
                    transaction_id=transaction.transaction_id
                )
                
                await ctx.send(sender, response)
                logger.info(f"支付成功: {msg.request_id}, 交易ID: {transaction.transaction_id}")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"支付失败: {msg.request_id}, 错误: {error_msg}")
                
                # 发送失败响应
                response = PaymentResponse(
                    request_id=msg.request_id,
                    success=False,
                    error_message=error_msg
                )
                
                await ctx.send(sender, response)
        
        @self.agent.on_message(model=BalanceRequest)
        async def handle_balance_request(ctx: Context, sender: str, msg: BalanceRequest) -> None:
            """处理余额查询请求"""
            logger.info(f"收到余额查询请求 from {sender}")
            
            try:
                balance_info = await coinremitter_service.get_all_balances()
                
                response = CoreBalanceResponse(
                    trc20_balance=balance_info.trc20_balance,
                    erc20_balance=balance_info.erc20_balance,
                    total_balance=balance_info.total_balance,
                    updated_at=balance_info.updated_at
                )
                
                await ctx.send(sender, response)
                logger.info(f"余额查询成功: 总余额 {balance_info.total_balance} USDT")
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"余额查询失败: {error_msg}")
        
        @self.agent.on_event("startup")
        async def startup_handler(ctx: Context) -> None:
            """启动事件处理器"""
            logger.info(f"钱包Agent启动: {ctx.agent.name}")
            logger.info(f"Agent地址: {ctx.agent.address}")
            
            # 如果余额不足，尝试充值（测试网络）
            try:
                await fund_agent_if_low(ctx.agent.wallet.address())
                logger.info("Agent充值检查完成")
            except Exception as e:
                logger.warning(f"Agent充值检查失败: {e}")
        
        @self.agent.on_interval(period=300.0)  # 每5分钟
        async def health_check(ctx: Context) -> None:
            """定期健康检查"""
            try:
                health_status = await coinremitter_service.health_check()
                logger.info(f"健康检查结果: {health_status}")
                
                # 检查余额
                balance_info = await coinremitter_service.get_all_balances()
                logger.info(f"当前余额: TRC20={balance_info.trc20_balance}, ERC20={balance_info.erc20_balance}")
                
            except Exception as e:
                logger.error(f"健康检查失败: {e}")
    
    async def send_stablecoin(
        self,
        recipient: str,
        amount: float,
        network: NetworkType = NetworkType.TRC20
    ) -> TransactionResponse:
        """发送稳定币
        
        Args:
            recipient: 接收地址
            amount: 发送金额
            network: 网络类型
            
        Returns:
            TransactionResponse: 交易响应
        """
        try:
            logger.info(f"发送稳定币: {amount} USDT -> {recipient} ({network})")
            
            # 验证参数
            if amount <= 0:
                raise ValueError("发送金额必须大于0")
            
            if not recipient:
                raise ValueError("接收地址不能为空")
            
            # 检查余额
            balance_amount = await coinremitter_service.get_balance_amount(network)
            if balance_amount < amount:
                raise InsufficientFundsException(
                    f"余额不足: 需要 {amount} USDT, 当前余额 {balance_amount} USDT"
                )
            
            # 执行转账
            transaction = await coinremitter_service.withdraw(
                amount=amount,
                address=recipient,
                network=network
            )
            
            logger.info(f"转账成功: {transaction.transaction_id}")
            return transaction
            
        except Exception as e:
            logger.error(f"转账失败: {str(e)}")
            raise AgentException(f"转账失败: {str(e)}")
    
    def run(self, show_info: bool = True) -> None:
        """运行Agent"""
        if show_info:
            logger.info(f"启动钱包Agent: {self.agent.name}")
            logger.info(f"监听端口: {settings.agent_port}")
        
        self.agent.run()
    
    async def run_async(self) -> None:
        """异步运行Agent"""
        logger.info(f"异步启动钱包Agent: {self.agent.name}")
        await self.agent.run_async()
    
    @property
    def address(self) -> str:
        """获取Agent地址"""
        return str(self.agent.address)
    
    @property
    def name(self) -> str:
        """获取Agent名称"""
        return self.agent.name


# 全局钱包Agent实例
wallet_agent = WalletAgent() 