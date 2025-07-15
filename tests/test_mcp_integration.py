"""MCP系统集成测试
测试支付流程、Agent通信和API接口
"""

import asyncio
import json
from datetime import datetime
from typing import Dict, Any
from unittest.mock import AsyncMock, patch

import pytest
import httpx
from fastapi.testclient import TestClient

from src.main import app
from src.core.models import NetworkType, PaymentStatus
from src.core.config import settings
from src.services.coinremitter import coinremitter_service
from src.services.dia_oracle import dia_oracle_service
from src.agent.wallet import wallet_agent


# 测试客户端
client = TestClient(app)


class TestMCPIntegration:
    """MCP系统集成测试类"""
    
    @pytest.fixture(autouse=True)
    def setup_method(self):
        """测试设置"""
        # 模拟配置，避免真实API调用
        self.mock_coinremitter_response = {
            "flag": 1,
            "data": {
                "address": "TTest123...MockAddress",
                "amount": "10.000000",
                "qr_code": "https://mock-qr-code.png",
                "url": "https://mock-payment-url.com",
                "invoice_id": "TEST_INVOICE_123"
            }
        }
        
        self.mock_dia_response = {
            "Price": 1.0001,
            "Time": datetime.utcnow().isoformat() + "Z"
        }
    
    @pytest.mark.asyncio
    async def test_health_check(self):
        """测试健康检查接口"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] in ["healthy", "unhealthy"]
        assert "timestamp" in data
        assert "services" in data
    
    @pytest.mark.asyncio
    async def test_get_usdt_price(self):
        """测试USDT价格查询"""
        with patch('httpx.AsyncClient.get') as mock_get:
            mock_response = AsyncMock()
            mock_response.raise_for_status.return_value = None
            mock_response.json.return_value = self.mock_dia_response
            mock_get.return_value = mock_response
            
            response = client.get("/api/v1/price")
            assert response.status_code == 200
            
            data = response.json()
            assert data["symbol"] == "USDT"
            assert "price_usd" in data
            assert "timestamp" in data
    
    @pytest.mark.asyncio
    async def test_create_payment_request(self):
        """测试创建支付请求"""
        with patch('src.services.coinremitter.coinremitter_service._make_request') as mock_coinremitter, \
             patch('src.services.dia_oracle.dia_oracle_service.get_usdt_price') as mock_dia:
            
            # 模拟DIA Oracle响应
            from src.core.models import PriceResponse
            mock_dia.return_value = PriceResponse(
                symbol="USDT",
                price_usd=1.0001,
                timestamp=datetime.utcnow(),
                source="DIA Oracle"
            )
            
            # 模拟Coinremitter响应
            mock_coinremitter.return_value = self.mock_coinremitter_response["data"]
            
            # 发送支付请求
            payment_request = {
                "amount_usd": 10.0,
                "network": "trc20",
                "description": "Test payment",
                "callback_url": "https://example.com/callback"
            }
            
            response = client.post("/api/v1/pay", json=payment_request)
            assert response.status_code == 200
            
            data = response.json()
            assert data["amount_usd"] == 10.0
            assert data["network"] == "trc20"
            assert data["status"] == "pending"
            assert "payment_address" in data
            assert "invoice_id" in data
    
    @pytest.mark.asyncio
    async def test_payment_callback_verification(self):
        """测试支付回调验证"""
        # 模拟Coinremitter回调数据
        callback_data = {
            "invoice_id": "TEST_INVOICE_123",
            "status": "success",
            "amount": "10.000000",
            "txid": "0x123...mockTxHash"
        }
        
        # 生成模拟签名
        with patch('src.services.coinremitter.coinremitter_service.verify_webhook') as mock_verify:
            mock_verify.return_value = True
            
            # 发送回调请求
            response = client.post(
                "/api/v1/callback/trc20",
                data=callback_data,
                headers={"X-Coinremitter-Signature": "mock_signature"}
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "success"
    
    @pytest.mark.asyncio
    async def test_get_balance(self):
        """测试余额查询"""
        with patch('src.services.coinremitter.coinremitter_service._make_request') as mock_request:
            # 模拟TRC20和ERC20余额响应
            mock_request.side_effect = [
                {"balance": "100.000000"},  # TRC20余额
                {"balance": "50.000000"}    # ERC20余额
            ]
            
            response = client.get("/api/v1/balance")
            assert response.status_code == 200
            
            data = response.json()
            assert data["trc20_balance"] == 100.0
            assert data["erc20_balance"] == 50.0
            assert data["total_balance"] == 150.0
    
    @pytest.mark.asyncio
    async def test_send_stablecoin(self):
        """测试发送稳定币"""
        with patch('src.services.coinremitter.coinremitter_service.get_balance') as mock_balance, \
             patch('src.services.coinremitter.coinremitter_service._make_request') as mock_request:
            
            # 模拟足够的余额
            mock_balance.return_value = 100.0
            
            # 模拟提现响应
            mock_request.return_value = {
                "id": "TX_123",
                "txid": "0x456...mockTxHash",
                "status": "pending"
            }
            
            send_request = {
                "recipient": "TTest456...RecipientAddress",
                "amount": 5.0,
                "network": "trc20"
            }
            
            response = client.post("/api/v1/send", json=send_request)
            assert response.status_code == 200
            
            data = response.json()
            assert data["amount"] == 5.0
            assert data["network"] == "trc20"
            assert data["recipient"] == send_request["recipient"]
            assert "transaction_id" in data
    
    @pytest.mark.asyncio
    async def test_insufficient_funds(self):
        """测试余额不足的情况"""
        with patch('src.services.coinremitter.coinremitter_service.get_balance') as mock_balance:
            # 模拟余额不足
            mock_balance.return_value = 1.0
            
            send_request = {
                "recipient": "TTest456...RecipientAddress",
                "amount": 10.0,  # 超过余额
                "network": "trc20"
            }
            
            response = client.post("/api/v1/send", json=send_request)
            assert response.status_code == 422  # 余额不足
    
    @pytest.mark.asyncio
    async def test_invalid_network(self):
        """测试无效网络类型"""
        payment_request = {
            "amount_usd": 10.0,
            "network": "invalid_network",  # 无效网络
            "description": "Test payment"
        }
        
        response = client.post("/api/v1/pay", json=payment_request)
        assert response.status_code == 422  # 验证错误
    
    @pytest.mark.asyncio
    async def test_webhook_signature_verification_failure(self):
        """测试Webhook签名验证失败"""
        callback_data = {
            "invoice_id": "TEST_INVOICE_123",
            "status": "success",
            "amount": "10.000000"
        }
        
        with patch('src.services.coinremitter.coinremitter_service.verify_webhook') as mock_verify:
            mock_verify.return_value = False  # 签名验证失败
            
            response = client.post(
                "/api/v1/callback/trc20",
                data=callback_data,
                headers={"X-Coinremitter-Signature": "invalid_signature"}
            )
            
            assert response.status_code == 400  # 签名验证失败
    
    @pytest.mark.asyncio
    async def test_agent_wallet_functionality(self):
        """测试Agent钱包功能"""
        with patch('src.services.coinremitter.coinremitter_service.get_balance') as mock_balance, \
             patch('src.services.coinremitter.coinremitter_service.withdraw') as mock_withdraw:
            
            # 模拟余额和提现
            mock_balance.return_value = 100.0
            
            from src.core.models import TransactionResponse
            mock_withdraw.return_value = TransactionResponse(
                transaction_id="AGENT_TX_123",
                transaction_hash="0x789...agentTxHash",
                status="pending",
                amount=5.0,
                network=NetworkType.TRC20,
                recipient="TAgent123...TestAddress",
                created_at=datetime.utcnow()
            )
            
            # 测试Agent发送稳定币
            result = await wallet_agent.send_stablecoin(
                recipient="TAgent123...TestAddress",
                amount=5.0,
                network=NetworkType.TRC20
            )
            
            assert result.amount == 5.0
            assert result.network == NetworkType.TRC20
            assert result.transaction_id == "AGENT_TX_123"


class TestAPIErrorHandling:
    """API错误处理测试"""
    
    def test_validation_errors(self):
        """测试数据验证错误"""
        # 测试负金额
        response = client.post("/api/v1/pay", json={
            "amount_usd": -10.0,
            "network": "trc20"
        })
        assert response.status_code == 422
        
        # 测试空接收地址
        response = client.post("/api/v1/send", json={
            "recipient": "",
            "amount": 5.0,
            "network": "trc20"
        })
        assert response.status_code == 422
    
    def test_network_errors(self):
        """测试网络错误处理"""
        with patch('httpx.AsyncClient.get') as mock_get:
            # 模拟网络超时
            mock_get.side_effect = httpx.TimeoutException("Request timeout")
            
            response = client.get("/api/v1/price")
            assert response.status_code == 500


class TestPaymentFlow:
    """完整支付流程测试"""
    
    @pytest.mark.asyncio
    async def test_complete_payment_flow(self):
        """测试完整的支付流程"""
        with patch('src.services.dia_oracle.dia_oracle_service.get_usdt_price') as mock_price, \
             patch('src.services.coinremitter.coinremitter_service._make_request') as mock_coinremitter, \
             patch('src.services.coinremitter.coinremitter_service.verify_webhook') as mock_verify:
            
            # 1. 获取价格
            from src.core.models import PriceResponse
            mock_price.return_value = PriceResponse(
                symbol="USDT",
                price_usd=1.0001,
                timestamp=datetime.utcnow(),
                source="DIA Oracle"
            )
            
            # 2. 创建支付
            mock_coinremitter.return_value = {
                "address": "TTestFlow123...PaymentAddress",
                "amount": "10.001000",
                "qr_code": "https://flow-qr-code.png",
                "url": "https://flow-payment-url.com"
            }
            
            payment_response = client.post("/api/v1/pay", json={
                "amount_usd": 10.0,
                "network": "trc20",
                "description": "Flow test payment"
            })
            
            assert payment_response.status_code == 200
            payment_data = payment_response.json()
            
            # 3. 模拟支付完成回调
            mock_verify.return_value = True
            
            callback_response = client.post(
                "/api/v1/callback/trc20",
                data={
                    "invoice_id": payment_data["invoice_id"],
                    "status": "success",
                    "amount": payment_data["amount_usdt"],
                    "txid": "0xFlowTest...CompleteHash"
                },
                headers={"X-Coinremitter-Signature": "valid_signature"}
            )
            
            assert callback_response.status_code == 200
            callback_data = callback_response.json()
            assert callback_data["status"] == "success"


# pytest配置
def pytest_configure(config):
    """pytest配置"""
    import sys
    import os
    
    # 添加源代码路径到Python路径
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))


if __name__ == "__main__":
    # 运行测试
    pytest.main([__file__, "-v", "--tb=short"]) 