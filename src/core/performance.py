"""性能优化模块
包含HTTP连接池、缓存、内存管理等性能优化功能
"""

import asyncio
import time
import weakref
from typing import Any, Dict, Optional, Union, Callable
from datetime import datetime, timedelta
from dataclasses import dataclass, field
from contextlib import asynccontextmanager

import httpx
from loguru import logger


@dataclass
class CacheItem:
    """缓存项"""
    value: Any
    created_at: float
    ttl: float
    access_count: int = 0
    last_access: float = field(default_factory=time.time)


class MemoryCache:
    """内存缓存管理器"""
    
    def __init__(self, max_size: int = 1000, default_ttl: float = 300.0):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: Dict[str, CacheItem] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        # 延迟启动清理任务，直到有事件循环运行
    
    def _start_cleanup(self):
        """启动清理任务"""
        try:
            if self._cleanup_task is None or self._cleanup_task.done():
                self._cleanup_task = asyncio.create_task(self._cleanup_expired())
        except RuntimeError:
            # 没有运行的事件循环，稍后启动
            pass
    
    async def _cleanup_expired(self):
        """清理过期缓存"""
        while True:
            try:
                await asyncio.sleep(60)  # 每分钟清理一次
                current_time = time.time()
                expired_keys = []
                
                for key, item in self._cache.items():
                    if current_time - item.created_at > item.ttl:
                        expired_keys.append(key)
                
                for key in expired_keys:
                    del self._cache[key]
                
                # 如果缓存太大，移除最少使用的项
                if len(self._cache) > self.max_size:
                    sorted_items = sorted(
                        self._cache.items(),
                        key=lambda x: (x[1].access_count, x[1].last_access)
                    )
                    
                    remove_count = len(self._cache) - self.max_size
                    for key, _ in sorted_items[:remove_count]:
                        del self._cache[key]
                
                if expired_keys:
                    logger.debug(f"清理了 {len(expired_keys)} 个过期缓存项")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"缓存清理错误: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """获取缓存值"""
        item = self._cache.get(key)
        if item is None:
            return None
        
        current_time = time.time()
        if current_time - item.created_at > item.ttl:
            del self._cache[key]
            return None
        
        # 更新访问统计
        item.access_count += 1
        item.last_access = current_time
        return item.value
    
    def set(self, key: str, value: Any, ttl: Optional[float] = None) -> None:
        """设置缓存值"""
        if ttl is None:
            ttl = self.default_ttl
        
        self._cache[key] = CacheItem(
            value=value,
            created_at=time.time(),
            ttl=ttl
        )
        
        # 确保清理任务已启动
        if self._cleanup_task is None:
            self._start_cleanup()
    
    def delete(self, key: str) -> bool:
        """删除缓存项"""
        if key in self._cache:
            del self._cache[key]
            return True
        return False
    
    def clear(self) -> None:
        """清空缓存"""
        self._cache.clear()
    
    def stats(self) -> Dict[str, Any]:
        """获取缓存统计"""
        return {
            "size": len(self._cache),
            "max_size": self.max_size,
            "default_ttl": self.default_ttl
        }


class HTTPClientManager:
    """HTTP客户端连接池管理器"""
    
    def __init__(self, 
                 max_connections: int = 100,
                 max_keepalive_connections: int = 20,
                 keepalive_expiry: float = 30.0,
                 timeout: float = 30.0):
        
        self.limits = httpx.Limits(
            max_connections=max_connections,
            max_keepalive_connections=max_keepalive_connections,
            keepalive_expiry=keepalive_expiry
        )
        
        self.timeout = httpx.Timeout(timeout)
        self._client: Optional[httpx.AsyncClient] = None
        self._lock = asyncio.Lock()
    
    async def get_client(self) -> httpx.AsyncClient:
        """获取HTTP客户端（单例模式）"""
        if self._client is None or self._client.is_closed:
            async with self._lock:
                if self._client is None or self._client.is_closed:
                    self._client = httpx.AsyncClient(
                        limits=self.limits,
                        timeout=self.timeout,
                        headers={
                            "User-Agent": "FinAgent-MCP-Server/1.0",
                            "Accept": "application/json",
                            "Connection": "keep-alive"
                        }
                    )
        return self._client
    
    async def close(self):
        """关闭客户端"""
        if self._client and not self._client.is_closed:
            await self._client.aclose()
    
    @asynccontextmanager
    async def request(self, method: str, url: str, **kwargs):
        """发起HTTP请求的上下文管理器"""
        client = await self.get_client()
        try:
            response = await client.request(method, url, **kwargs)
            yield response
        finally:
            # 不需要手动关闭response，由客户端管理
            pass


class CircuitBreaker:
    """断路器模式实现"""
    
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: type = Exception):
        
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs):
        """调用函数，应用断路器逻辑"""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
            
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """检查是否应该尝试重置断路器"""
        return (self.last_failure_time is not None and 
                time.time() - self.last_failure_time >= self.recovery_timeout)
    
    def _on_success(self):
        """成功时的处理"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """失败时的处理"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"


class PerformanceMonitor:
    """性能监控器"""
    
    def __init__(self):
        self.metrics: Dict[str, list] = {}
        self._weak_refs: weakref.WeakSet = weakref.WeakSet()
    
    def record_execution_time(self, operation: str, duration: float):
        """记录执行时间"""
        if operation not in self.metrics:
            self.metrics[operation] = []
        
        self.metrics[operation].append({
            "duration": duration,
            "timestamp": time.time()
        })
        
        # 保持最近1000条记录
        if len(self.metrics[operation]) > 1000:
            self.metrics[operation] = self.metrics[operation][-1000:]
    
    def get_stats(self, operation: str) -> Dict[str, float]:
        """获取操作统计"""
        if operation not in self.metrics or not self.metrics[operation]:
            return {}
        
        durations = [m["duration"] for m in self.metrics[operation]]
        
        return {
            "count": len(durations),
            "avg": sum(durations) / len(durations),
            "min": min(durations),
            "max": max(durations),
            "recent_avg": sum(durations[-10:]) / min(len(durations), 10)
        }
    
    def monitor_function(self, operation_name: str):
        """装饰器：监控函数执行时间"""
        def decorator(func):
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    start_time = time.time()
                    try:
                        result = await func(*args, **kwargs)
                        return result
                    finally:
                        duration = time.time() - start_time
                        self.record_execution_time(operation_name, duration)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    start_time = time.time()
                    try:
                        result = func(*args, **kwargs)
                        return result
                    finally:
                        duration = time.time() - start_time
                        self.record_execution_time(operation_name, duration)
                return sync_wrapper
        return decorator


class ResourceManager:
    """资源管理器"""
    
    def __init__(self):
        self.resources: Dict[str, Any] = {}
        self._cleanup_tasks: list = []
    
    def register_resource(self, name: str, resource: Any, cleanup_func: Optional[Callable] = None):
        """注册资源"""
        self.resources[name] = resource
        
        if cleanup_func:
            self._cleanup_tasks.append((name, cleanup_func))
    
    async def cleanup_all(self):
        """清理所有资源"""
        for name, cleanup_func in self._cleanup_tasks:
            try:
                if asyncio.iscoroutinefunction(cleanup_func):
                    await cleanup_func()
                else:
                    cleanup_func()
                logger.debug(f"资源 {name} 清理完成")
            except Exception as e:
                logger.error(f"清理资源 {name} 失败: {e}")
    
    def get_resource(self, name: str) -> Optional[Any]:
        """获取资源"""
        return self.resources.get(name)


# 全局实例
memory_cache = MemoryCache(max_size=1000, default_ttl=300.0)
http_client_manager = HTTPClientManager()
performance_monitor = PerformanceMonitor()
resource_manager = ResourceManager()

# 注册HTTP客户端资源
resource_manager.register_resource(
    "http_client", 
    http_client_manager, 
    http_client_manager.close
) 