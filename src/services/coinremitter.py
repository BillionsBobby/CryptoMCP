"""Coinremitter支付服务
处理USDT TRC20和ERC20网络的支付功能
"""

from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
import httpx
from loguru import logger

from ..core.config import settings
from ..core.performance import http_client_manager, memory_cache, performance_monitor
from ..core.exceptions import CoinremitterException, NetworkException, ValidationException
from ..core.models import (
    NetworkType, PaymentStatus, PaymentResponse, TransactionResponse, 
    BalanceResponse, InvoiceStatus
)
from ..core.utils import verify_hmac_signature, generate_invoice_id, get_current_timestamp


class CoinremitterService:
    """Coinremitter API服务类"""
    
    def __init__(self) -> None:
        self.trc20_base_url = "https://coinremitter.com/api/v3/USDTTRC20"
        self.erc20_base_url = "https://coinremitter.com/api/v3/USDTERC20"
        self.timeout = 60.0
        
    def _get_network_config(self, network: NetworkType) -> Dict[str, str]:
        """获取网络配置
        
        Args:
            network: 网络类型
            
        Returns:
            Dict: 网络配置信息
        """
        if network == NetworkType.TRC20:
            return {
                "base_url": self.trc20_base_url,
                "api_key": settings.coinremitter_trc20_api_key,
                "password": settings.coinremitter_trc20_password,
                "webhook_secret": settings.coinremitter_trc20_webhook_secret,
            }
        elif network == NetworkType.ERC20:
            return {
                "base_url": self.erc20_base_url,
                "api_key": settings.coinremitter_erc20_api_key,
                "password": settings.coinremitter_erc20_password,
                "webhook_secret": settings.coinremitter_erc20_webhook_secret,
            }
        else:
            raise ValidationException(f"不支持的网络类型: {network}")
    
    @performance_monitor.monitor_function("coinremitter_api_call")
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        network: NetworkType,
        data: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """发起API请求
        
        Args:
            method: HTTP方法
            endpoint: API端点
            network: 网络类型
            data: 请求数据
            
        Returns:
            Dict: API响应数据
        """
        config = self._get_network_config(network)
        url = f"{config['base_url']}/{endpoint}"
        
        # 准备请求数据
        payload = {
            "api_key": config["api_key"],
            "password": config["password"],
        }
        if data:
            payload.update(data)
        
        try:
            async with http_client_manager.request(
                method.upper(), 
                url, 
                params=payload if method.upper() == "GET" else None,
                data=payload if method.upper() != "GET" else None,
                timeout=self.timeout
            ) as response:
                response.raise_for_status()
                result = response.json()
                
                # 检查API响应状态
                if result.get("flag") != 1:
                    error_msg = result.get("msg", "未知错误")
                    logger.error(f"Coinremitter API错误: {error_msg}")
                    raise CoinremitterException(f"API调用失败: {error_msg}")
                
                return result.get("data", {})
                
        except httpx.HTTPStatusError as e:
            error_msg = f"Coinremitter HTTP错误: {e.response.status_code}"
            logger.error(error_msg)
            raise CoinremitterException(error_msg, {"status_code": e.response.status_code})
            
        except httpx.RequestError as e:
            error_msg = f"Coinremitter网络请求错误: {str(e)}"
            logger.error(error_msg)
            raise NetworkException(error_msg)
    
    async def create_invoice(
        self,
        amount: float,
        network: NetworkType,
        description: Optional[str] = None,
        callback_url: Optional[str] = None
    ) -> PaymentResponse:
        """创建支付发票
        
        Args:
            amount: USDT金额
            network: 网络类型
            description: 支付描述
            callback_url: 回调URL
            
        Returns:
            PaymentResponse: 支付响应
        """
        invoice_id = generate_invoice_id()
        
        payload = {
            "amount": str(amount),
            "name": description or f"Payment {invoice_id}",
            "currency": "USDT",
            "expire_time": str(settings.payment_timeout // 60),  # 转换为分钟
        }
        
        if callback_url:
            payload["notify_url"] = callback_url
        
        try:
            data = await self._make_request("POST", "get-invoice", network, payload)
            
            # 计算过期时间
            expires_at = datetime.utcnow() + timedelta(seconds=settings.payment_timeout)
            
            response = PaymentResponse(
                invoice_id=invoice_id,
                payment_address=data.get("address", ""),
                amount_usdt=amount,
                amount_usd=amount,  # 这里需要根据实际汇率计算
                network=network,
                status=PaymentStatus.PENDING,
                expires_at=expires_at,
                qr_code_url=data.get("qr_code", ""),
                payment_url=data.get("url", "")
            )
            
            logger.info(f"创建发票成功: {invoice_id}, 网络: {network}, 金额: {amount} USDT")
            return response
            
        except Exception as e:
            logger.error(f"创建发票失败: {str(e)}")
            raise
    
    async def get_balance(self, network: NetworkType) -> BalanceResponse:
        """获取钱包余额
        
        Args:
            network: 网络类型
            
        Returns:
            BalanceResponse: 余额信息
        """
        try:
            data = await self._make_request("GET", "get-balance", network)
            balance = float(data.get("balance", 0))
            logger.info(f"获取{network}余额: {balance} USDT")
            
            return BalanceResponse(
                balance=balance,
                network=network,
                updated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"获取余额失败: {str(e)}")
            raise
    
    async def get_balance_amount(self, network: NetworkType) -> float:
        """获取钱包余额数值
        
        Args:
            network: 网络类型
            
        Returns:
            float: 余额数值
        """
        balance_response = await self.get_balance(network)
        return balance_response.balance
    
    async def get_all_balances(self) -> BalanceResponse:
        """获取所有网络余额
        
        Returns:
            BalanceResponse: 余额信息
        """
        try:
            trc20_balance = await self.get_balance_amount(NetworkType.TRC20)
            erc20_balance = await self.get_balance_amount(NetworkType.ERC20)
            
            return BalanceResponse(
                trc20_balance=trc20_balance,
                erc20_balance=erc20_balance,
                total_balance=trc20_balance + erc20_balance,
                updated_at=datetime.utcnow()
            )
            
        except Exception as e:
            logger.error(f"获取所有余额失败: {str(e)}")
            raise
    
    async def withdraw(
        self,
        amount: float,
        address: str,
        network: NetworkType
    ) -> TransactionResponse:
        """发起提现
        
        Args:
            amount: 提现金额
            address: 接收地址
            network: 网络类型
            
        Returns:
            TransactionResponse: 交易响应
        """
        payload = {
            "amount": str(amount),
            "address": address,
        }
        
        try:
            data = await self._make_request("POST", "withdraw", network, payload)
            
            response = TransactionResponse(
                transaction_id=data.get("id", ""),
                transaction_hash=data.get("txid", ""),
                status=data.get("status", "pending"),
                amount=amount,
                network=network,
                recipient=address,
                created_at=datetime.utcnow()
            )
            
            logger.info(f"提现请求成功: {amount} USDT -> {address} ({network})")
            return response
            
        except Exception as e:
            logger.error(f"提现失败: {str(e)}")
            raise
    
    async def get_transaction(
        self,
        transaction_id: str,
        network: NetworkType
    ) -> Optional[Dict[str, Any]]:
        """获取交易详情
        
        Args:
            transaction_id: 交易ID
            network: 网络类型
            
        Returns:
            Optional[Dict]: 交易详情
        """
        payload = {"id": transaction_id}
        
        try:
            data = await self._make_request("GET", "get-transaction", network, payload)
            logger.info(f"获取交易详情成功: {transaction_id}")
            return data
            
        except Exception as e:
            logger.error(f"获取交易详情失败: {str(e)}")
            return None
    
    def verify_webhook(
        self,
        payload: str,
        signature: str,
        network: NetworkType
    ) -> bool:
        """验证Webhook签名
        
        Args:
            payload: Webhook负载
            signature: 签名
            network: 网络类型
            
        Returns:
            bool: 签名是否有效
        """
        config = self._get_network_config(network)
        secret = config["webhook_secret"]
        
        return verify_hmac_signature(payload, signature, secret)
    
    async def health_check(self) -> Dict[str, bool]:
        """健康检查
        
        Returns:
            Dict: 各网络的健康状态
        """
        results = {}
        
        for network in [NetworkType.TRC20, NetworkType.ERC20]:
            try:
                await self.get_balance(network)
                results[network.value] = True
            except Exception as e:
                logger.error(f"{network}网络健康检查失败: {str(e)}")
                results[network.value] = False
        
        return results


# 全局服务实例
coinremitter_service = CoinremitterService() 