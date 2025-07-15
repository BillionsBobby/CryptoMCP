"""DIA Oracle价格服务
获取USDT实时价格数据
"""

from datetime import datetime
from typing import Dict, Any, Optional
import httpx
from loguru import logger

from ..core.config import settings
from ..core.performance import http_client_manager, memory_cache, performance_monitor
from ..core.exceptions import DIAOracleException, NetworkException
from ..core.models import PriceResponse


class DIAOracleService:
    """DIA Oracle API服务类"""
    
    def __init__(self) -> None:
        self.base_url = settings.dia_oracle_base_url
        self.timeout = 30.0
        
    @performance_monitor.monitor_function("dia_oracle_price_fetch")
    async def get_usdt_price(self) -> PriceResponse:
        """获取USDT价格
        
        Returns:
            PriceResponse: 价格信息
            
        Raises:
            DIAOracleException: API调用异常
        """
        # 尝试从缓存获取价格
        cache_key = "usdt_price"
        cached_price = memory_cache.get(cache_key)
        if cached_price:
            logger.debug("使用缓存的USDT价格")
            return cached_price
        
        try:
            async with http_client_manager.request("GET", self.base_url, timeout=self.timeout) as response:
                response.raise_for_status()
                
                data = response.json()
                logger.info(f"获取USDT价格成功: ${data.get('Price', 0)}")
                
                price_response = PriceResponse(
                    symbol="USDT",
                    price_usd=float(data.get("Price", 1.0)),
                    timestamp=datetime.fromisoformat(
                        data.get("Time", datetime.utcnow().isoformat()).replace("Z", "+00:00")
                    ),
                    source="DIA Oracle"
                )
                
                # 缓存价格数据60秒
                memory_cache.set(cache_key, price_response, ttl=60.0)
                return price_response
                
        except httpx.HTTPStatusError as e:
            error_msg = f"DIA Oracle API请求失败: {e.response.status_code}"
            logger.error(error_msg)
            raise DIAOracleException(error_msg, {"status_code": e.response.status_code})
            
        except httpx.RequestError as e:
            error_msg = f"DIA Oracle网络请求错误: {str(e)}"
            logger.error(error_msg)
            raise NetworkException(error_msg)
            
        except (ValueError, KeyError) as e:
            error_msg = f"DIA Oracle响应数据解析错误: {str(e)}"
            logger.error(error_msg)
            raise DIAOracleException(error_msg)
    
    async def calculate_usdt_amount(self, usd_amount: float) -> float:
        """根据USD金额计算需要的USDT数量
        
        Args:
            usd_amount: USD金额
            
        Returns:
            float: USDT数量
        """
        try:
            price_data = await self.get_usdt_price()
            usdt_amount = usd_amount / price_data.price_usd
            
            logger.info(f"USD ${usd_amount} = USDT {usdt_amount:.6f} (价格: ${price_data.price_usd})")
            return usdt_amount
            
        except Exception as e:
            logger.error(f"计算USDT金额失败: {str(e)}")
            # 如果价格获取失败，使用1:1比率作为fallback
            logger.warning("使用USDT:USD = 1:1的fallback比率")
            return usd_amount
    
    async def health_check(self) -> bool:
        """健康检查
        
        Returns:
            bool: 服务是否正常
        """
        try:
            await self.get_usdt_price()
            return True
        except Exception as e:
            logger.error(f"DIA Oracle健康检查失败: {str(e)}")
            return False


# 全局服务实例
dia_oracle_service = DIAOracleService() 