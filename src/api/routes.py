"""API路由模块
定义支付相关的REST API接口
"""

from datetime import datetime
from typing import Dict, Any

from fastapi import APIRouter, HTTPException, Request, Depends, BackgroundTasks
from fastapi.responses import JSONResponse
from loguru import logger

from ..core.config import settings
from ..core.models import (
    CreatePaymentRequest, PaymentResponse, SendStablecoinRequest,
    TransactionResponse, BalanceResponse, ErrorResponse, NetworkType
)
from ..core.exceptions import (
    PaymentException, ValidationException, InsufficientFundsException,
    WebhookException
)
from ..core.utils import verify_hmac_signature, validate_usdt_amount
from ..services.coinremitter import coinremitter_service
from ..services.dia_oracle import dia_oracle_service
from ..agent.wallet import wallet_agent


# 创建路由器
router = APIRouter(prefix="/api/v1", tags=["MCP Payment"])


@router.post("/pay", response_model=PaymentResponse)
async def create_payment(request: CreatePaymentRequest) -> PaymentResponse:
    """创建支付请求
    
    根据USD金额创建USDT支付发票
    """
    try:
        logger.info(f"创建支付请求: ${request.amount_usd} USD, 网络: {request.network}")
        
        # 验证网络类型
        if request.network not in [NetworkType.TRC20, NetworkType.ERC20]:
            raise ValidationException(f"不支持的网络类型: {request.network}")
        
        # 使用DIA Oracle获取USDT价格并计算所需USDT数量
        usdt_amount = await dia_oracle_service.calculate_usdt_amount(request.amount_usd)
        
        # 验证USDT金额
        if not validate_usdt_amount(usdt_amount):
            raise ValidationException(
                f"USDT金额超出限制: {usdt_amount} (限制: {settings.min_payment_amount}-{settings.max_payment_amount})"
            )
        
        # 创建Coinremitter发票
        payment = await coinremitter_service.create_invoice(
            amount=usdt_amount,
            network=request.network,
            description=request.description,
            callback_url=request.callback_url
        )
        
        # 更新响应中的USD金额
        payment.amount_usd = request.amount_usd
        
        logger.info(f"支付请求创建成功: {payment.invoice_id}")
        return payment
        
    except ValidationException as e:
        logger.error(f"支付请求验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=str(e))
    except PaymentException as e:
        logger.error(f"支付请求创建失败: {e.message}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"支付请求处理异常: {str(e)}")
        raise HTTPException(status_code=500, detail="内部服务器错误")


@router.post("/callback/{network}")
async def payment_callback(
    network: str,
    request: Request,
    background_tasks: BackgroundTasks
) -> Dict[str, str]:
    """接收Coinremitter支付回调
    
    处理IPN回调并验证HMAC签名
    """
    try:
        # 验证网络类型
        network_type = NetworkType(network.lower())
        logger.info(f"收到{network_type}支付回调")
        
        # 获取请求体
        body = await request.body()
        payload = body.decode('utf-8')
        
        # 获取签名头
        signature = request.headers.get('X-Coinremitter-Signature', '')
        if not signature:
            raise WebhookException("缺少签名头")
        
        # 验证HMAC签名
        if not coinremitter_service.verify_webhook(payload, signature, network_type):
            raise WebhookException("签名验证失败")
        
        # 解析回调数据
        form_data = await request.form()
        callback_data = dict(form_data)
        
        logger.info(f"回调数据验证成功: {callback_data}")
        
        # 后台处理回调数据
        background_tasks.add_task(process_payment_callback, network_type, callback_data)
        
        return {"status": "success", "message": "回调处理成功"}
        
    except WebhookException as e:
        logger.error(f"Webhook处理失败: {e.message}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"回调处理异常: {str(e)}")
        raise HTTPException(status_code=500, detail="回调处理失败")


@router.post("/send", response_model=TransactionResponse)
async def send_stablecoin(request: SendStablecoinRequest) -> TransactionResponse:
    """Agent发送稳定币
    
    使用Agent钱包发送USDT到指定地址
    """
    try:
        logger.info(f"Agent发送稳定币: {request.amount} USDT -> {request.recipient} ({request.network})")
        
        # 验证网络类型
        if request.network not in [NetworkType.TRC20, NetworkType.ERC20]:
            raise ValidationException(f"不支持的网络类型: {request.network}")
        
        # 验证金额
        if not validate_usdt_amount(request.amount):
            raise ValidationException(
                f"金额超出限制: {request.amount} (限制: {settings.min_payment_amount}-{settings.max_payment_amount})"
            )
        
        # 使用Agent发送稳定币
        transaction = await wallet_agent.send_stablecoin(
            recipient=request.recipient,
            amount=request.amount,
            network=request.network
        )
        
        logger.info(f"稳定币发送成功: {transaction.transaction_id}")
        return transaction
        
    except ValidationException as e:
        logger.error(f"发送请求验证失败: {e.message}")
        raise HTTPException(status_code=400, detail=str(e))
    except InsufficientFundsException as e:
        logger.error(f"余额不足: {e.message}")
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        logger.error(f"发送稳定币异常: {str(e)}")
        raise HTTPException(status_code=500, detail="发送失败")


@router.get("/balance", response_model=BalanceResponse)
async def get_balance() -> BalanceResponse:
    """获取钱包余额"""
    try:
        logger.info("查询钱包余额")
        balance = await coinremitter_service.get_all_balances()
        logger.info(f"余额查询成功: 总计 {balance.total_balance} USDT")
        return balance
        
    except Exception as e:
        logger.error(f"余额查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail="余额查询失败")


@router.get("/health")
async def health_check() -> Dict[str, Any]:
    """健康检查接口"""
    try:
        # 检查各服务状态
        coinremitter_status = await coinremitter_service.health_check()
        dia_oracle_status = await dia_oracle_service.health_check()
        
        # 获取Agent信息
        agent_info = {
            "name": wallet_agent.name,
            "address": wallet_agent.address,
            "status": "online"
        }
        
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "services": {
                "coinremitter": coinremitter_status,
                "dia_oracle": dia_oracle_status,
                "wallet_agent": agent_info
            }
        }
        
        logger.info("健康检查完成")
        return health_status
        
    except Exception as e:
        logger.error(f"健康检查失败: {str(e)}")
        return {
            "status": "unhealthy",
            "timestamp": datetime.utcnow().isoformat(),
            "error": str(e)
        }


@router.get("/price")
async def get_usdt_price() -> Dict[str, Any]:
    """获取USDT当前价格"""
    try:
        price_data = await dia_oracle_service.get_usdt_price()
        return {
            "symbol": price_data.symbol,
            "price_usd": price_data.price_usd,
            "timestamp": price_data.timestamp.isoformat(),
            "source": price_data.source
        }
    except Exception as e:
        logger.error(f"价格查询失败: {str(e)}")
        raise HTTPException(status_code=500, detail="价格查询失败")


async def process_payment_callback(network: NetworkType, callback_data: Dict[str, Any]) -> None:
    """后台处理支付回调
    
    Args:
        network: 网络类型
        callback_data: 回调数据
    """
    try:
        logger.info(f"处理{network}支付回调: {callback_data}")
        
        # 提取关键信息
        invoice_id = callback_data.get('invoice_id', '')
        status = callback_data.get('status', '')
        amount = float(callback_data.get('amount', 0))
        txid = callback_data.get('txid', '')
        
        # 根据状态更新支付记录
        if status == 'success':
            logger.info(f"支付成功: {invoice_id}, 交易ID: {txid}, 金额: {amount} USDT")
            # 这里可以添加数据库更新逻辑或发送通知
        elif status == 'pending':
            logger.info(f"支付待确认: {invoice_id}")
        elif status == 'failed':
            logger.warning(f"支付失败: {invoice_id}")
        
        # 发送通知给相关Agent或外部系统
        # 这里可以实现Agent间通信或Webhook转发
        
    except Exception as e:
        logger.error(f"回调处理异常: {str(e)}")


# 注意：异常处理器应该在FastAPI应用实例上注册，而不是APIRouter上
# 这些异常处理器在main.py中的FastAPI应用上注册 