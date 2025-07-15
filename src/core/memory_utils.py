"""内存管理工具
包含内存使用监控、垃圾回收、内存泄漏检测等功能
"""

import gc
import psutil
import threading
import weakref
from typing import Dict, Any, List, Optional, Set
from dataclasses import dataclass
from datetime import datetime

from loguru import logger


@dataclass
class MemoryStats:
    """内存统计信息"""
    total_memory: int
    available_memory: int
    used_memory: int
    memory_percent: float
    process_memory: int
    process_memory_percent: float


class MemoryMonitor:
    """内存监控器"""
    
    def __init__(self, check_interval: float = 60.0, warning_threshold: float = 80.0):
        self.check_interval = check_interval
        self.warning_threshold = warning_threshold
        self.monitoring = False
        self._monitor_thread: Optional[threading.Thread] = None
        self._tracked_objects: Dict[str, weakref.WeakSet] = {}
    
    def start_monitoring(self):
        """开始内存监控"""
        if not self.monitoring:
            self.monitoring = True
            self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._monitor_thread.start()
            logger.info("内存监控已启动")
    
    def stop_monitoring(self):
        """停止内存监控"""
        self.monitoring = False
        if self._monitor_thread:
            self._monitor_thread.join()
        logger.info("内存监控已停止")
    
    def _monitor_loop(self):
        """监控循环"""
        import time
        
        while self.monitoring:
            try:
                stats = self.get_memory_stats()
                
                if stats.memory_percent > self.warning_threshold:
                    logger.warning(
                        f"内存使用率过高: {stats.memory_percent:.1f}% "
                        f"(进程: {stats.process_memory_percent:.1f}%)"
                    )
                    
                    # 触发垃圾回收
                    self.force_garbage_collection()
                
                # 每10分钟记录一次内存状态
                if int(time.time()) % 600 == 0:
                    logger.info(
                        f"内存状态: 系统 {stats.memory_percent:.1f}%, "
                        f"进程 {stats.process_memory_percent:.1f}%"
                    )
                
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"内存监控错误: {e}")
                time.sleep(self.check_interval)
    
    def get_memory_stats(self) -> MemoryStats:
        """获取内存统计信息"""
        # 系统内存
        memory = psutil.virtual_memory()
        
        # 进程内存
        process = psutil.Process()
        process_memory = process.memory_info()
        
        return MemoryStats(
            total_memory=memory.total,
            available_memory=memory.available,
            used_memory=memory.used,
            memory_percent=memory.percent,
            process_memory=process_memory.rss,
            process_memory_percent=(process_memory.rss / memory.total) * 100
        )
    
    def force_garbage_collection(self):
        """强制垃圾回收"""
        before_stats = self.get_memory_stats()
        
        # 执行垃圾回收
        collected = gc.collect()
        
        after_stats = self.get_memory_stats()
        freed_memory = before_stats.process_memory - after_stats.process_memory
        
        logger.info(
            f"垃圾回收完成: 回收对象 {collected} 个, "
            f"释放内存 {freed_memory / 1024 / 1024:.1f} MB"
        )
    
    def register_object_type(self, type_name: str, obj: Any):
        """注册对象类型用于跟踪"""
        if type_name not in self._tracked_objects:
            self._tracked_objects[type_name] = weakref.WeakSet()
        
        self._tracked_objects[type_name].add(obj)
    
    def get_object_counts(self) -> Dict[str, int]:
        """获取跟踪对象的数量"""
        return {
            type_name: len(weak_set) 
            for type_name, weak_set in self._tracked_objects.items()
        }


class MemoryLeakDetector:
    """内存泄漏检测器"""
    
    def __init__(self, check_interval: int = 300):  # 5分钟
        self.check_interval = check_interval
        self.snapshots: List[Dict[type, int]] = []
        self.max_snapshots = 20  # 保留最近20个快照
    
    def take_snapshot(self):
        """拍摄内存快照"""
        # 统计各类型对象数量
        type_counts = {}
        for obj in gc.get_objects():
            obj_type = type(obj)
            type_counts[obj_type] = type_counts.get(obj_type, 0) + 1
        
        self.snapshots.append(type_counts)
        
        # 保持快照数量限制
        if len(self.snapshots) > self.max_snapshots:
            self.snapshots.pop(0)
        
        logger.debug(f"内存快照已拍摄, 共 {len(type_counts)} 种对象类型")
    
    def detect_leaks(self) -> List[Dict[str, Any]]:
        """检测内存泄漏"""
        if len(self.snapshots) < 3:
            return []
        
        leaks = []
        
        # 比较最新和最早的快照
        latest = self.snapshots[-1]
        baseline = self.snapshots[0]
        
        for obj_type, latest_count in latest.items():
            baseline_count = baseline.get(obj_type, 0)
            growth = latest_count - baseline_count
            
            # 如果某类型对象增长超过100个，可能存在泄漏
            if growth > 100:
                growth_rate = growth / len(self.snapshots)
                
                leaks.append({
                    "type": obj_type.__name__,
                    "module": getattr(obj_type, "__module__", "unknown"),
                    "baseline_count": baseline_count,
                    "current_count": latest_count,
                    "growth": growth,
                    "growth_rate": growth_rate
                })
        
        # 按增长数量排序
        leaks.sort(key=lambda x: x["growth"], reverse=True)
        
        if leaks:
            logger.warning(f"检测到 {len(leaks)} 个潜在内存泄漏")
        
        return leaks


class ResourceCleaner:
    """资源清理器"""
    
    def __init__(self):
        self.cleanup_handlers: List[callable] = []
        self.periodic_cleaners: Dict[str, dict] = {}
    
    def register_cleanup_handler(self, handler: callable):
        """注册清理处理器"""
        self.cleanup_handlers.append(handler)
    
    def register_periodic_cleaner(self, name: str, cleaner: callable, interval: float):
        """注册周期性清理器"""
        self.periodic_cleaners[name] = {
            "cleaner": cleaner,
            "interval": interval,
            "last_run": 0
        }
    
    async def run_periodic_cleanup(self):
        """运行周期性清理"""
        import time
        
        current_time = time.time()
        
        for name, config in self.periodic_cleaners.items():
            if current_time - config["last_run"] >= config["interval"]:
                try:
                    if hasattr(config["cleaner"], "__call__"):
                        if hasattr(config["cleaner"], "__await__"):
                            await config["cleaner"]()
                        else:
                            config["cleaner"]()
                    
                    config["last_run"] = current_time
                    logger.debug(f"周期性清理 {name} 完成")
                    
                except Exception as e:
                    logger.error(f"周期性清理 {name} 失败: {e}")
    
    def cleanup_all(self):
        """执行所有清理处理器"""
        for handler in self.cleanup_handlers:
            try:
                if hasattr(handler, "__await__"):
                    # 异步函数需要在事件循环中调用
                    logger.warning(f"异步清理函数 {handler} 需要在事件循环中调用")
                else:
                    handler()
                logger.debug(f"清理处理器 {handler} 执行完成")
            except Exception as e:
                logger.error(f"清理处理器 {handler} 执行失败: {e}")


# 全局实例
memory_monitor = MemoryMonitor()
memory_leak_detector = MemoryLeakDetector()
resource_cleaner = ResourceCleaner()

# 注册基础清理函数
resource_cleaner.register_cleanup_handler(gc.collect)
resource_cleaner.register_periodic_cleaner("garbage_collection", gc.collect, interval=300)  # 5分钟
resource_cleaner.register_periodic_cleaner("memory_snapshot", memory_leak_detector.take_snapshot, interval=300)  # 5分钟 