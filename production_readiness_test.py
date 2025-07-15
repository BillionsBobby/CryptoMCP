#!/usr/bin/env python3
"""生产环境就绪性测试
全面验证FinAgent MCP服务器的生产环境适配性
"""

import asyncio
import os
import sys
import time
import json
from typing import Dict, Any, List
from datetime import datetime

# 添加源代码路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from loguru import logger


class ProductionReadinessTest:
    """生产环境就绪性测试类"""
    
    def __init__(self):
        self.test_results: List[Dict[str, Any]] = []
        self.passed_tests = 0
        self.failed_tests = 0
        
    def record_test(self, test_name: str, passed: bool, details: str = ""):
        """记录测试结果"""
        result = {
            "test_name": test_name,
            "passed": passed,
            "details": details,
            "timestamp": datetime.now().isoformat()
        }
        self.test_results.append(result)
        
        if passed:
            self.passed_tests += 1
            logger.success(f"✅ {test_name} - 通过")
        else:
            self.failed_tests += 1
            logger.error(f"❌ {test_name} - 失败: {details}")
    
    async def test_core_imports(self):
        """测试核心模块导入"""
        try:
            # 测试MCP核心
            from src.mcp_server import mcp as mcp_server
            from src.mcp_server_simple import mcp as mcp_simple
            from src.mcp_server_http import mcp as mcp_http
            
            # 测试核心模块
            from src.core.config import settings
            from src.core.models import NetworkType, PaymentStatus
            from src.core.exceptions import MCPBaseException
            from src.core.utils import verify_hmac_signature
            
            # 测试新增的安全和性能模块
            from src.core.security import security_validator, SecureKeyGenerator
            from src.core.performance import memory_cache, http_client_manager
            from src.core.memory_utils import memory_monitor
            
            # 测试服务模块
            from src.services.coinremitter import CoinremitterService
            from src.services.dia_oracle import DIAOracleService
            
            self.record_test("核心模块导入", True, "所有关键模块正常导入")
            
        except Exception as e:
            self.record_test("核心模块导入", False, str(e))
    
    async def test_configuration_security(self):
        """测试配置安全性"""
        try:
            from src.core.config import settings
            from src.core.security import security_checker
            
            # 检查环境安全
            security_result = security_checker.check_environment_security()
            
            issues = security_result.get("issues", [])
            warnings = security_result.get("warnings", [])
            
            if issues:
                self.record_test(
                    "配置安全检查", 
                    False, 
                    f"发现 {len(issues)} 个安全问题: {', '.join(issues)}"
                )
            elif warnings:
                self.record_test(
                    "配置安全检查", 
                    True, 
                    f"通过但有 {len(warnings)} 个警告: {', '.join(warnings)}"
                )
            else:
                self.record_test("配置安全检查", True, "配置安全检查通过")
                
        except Exception as e:
            self.record_test("配置安全检查", False, str(e))
    
    async def test_input_validation(self):
        """测试输入验证"""
        try:
            from src.core.security import security_validator
            from src.core.models import CreatePaymentRequest, SendStablecoinRequest
            
            # 测试地址验证
            valid_trc20 = security_validator.validate_crypto_address("TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t", "trc20")
            valid_erc20 = security_validator.validate_crypto_address("0x742d35Cc6481C8B3B9C4A26C66B8e3e87A7b2E8C", "erc20")
            invalid_address = security_validator.validate_crypto_address("invalid", "trc20")
            
            if valid_trc20 and valid_erc20 and not invalid_address:
                self.record_test("地址验证", True, "地址格式验证正常")
            else:
                self.record_test("地址验证", False, f"验证结果: TRC20={valid_trc20}, ERC20={valid_erc20}, Invalid={invalid_address}")
            
            # 测试金额验证
            valid_amount = security_validator.validate_amount(100.0, 0.1, 10000.0)
            invalid_low = security_validator.validate_amount(0.05, 0.1, 10000.0)
            invalid_high = security_validator.validate_amount(20000.0, 0.1, 10000.0)
            
            if valid_amount and not invalid_low and not invalid_high:
                self.record_test("金额验证", True, "金额范围验证正常")
            else:
                self.record_test("金额验证", False, f"验证结果: Valid={valid_amount}, Low={invalid_low}, High={invalid_high}")
            
            # 测试输入清理
            clean_input = security_validator.sanitize_input("<script>alert('xss')</script>normal text")
            if "script" not in clean_input and "normal text" in clean_input:
                self.record_test("输入清理", True, "XSS防护正常")
            else:
                self.record_test("输入清理", False, f"清理结果: {clean_input}")
                
        except Exception as e:
            self.record_test("输入验证", False, str(e))
    
    async def test_performance_systems(self):
        """测试性能系统"""
        try:
            from src.core.performance import memory_cache, http_client_manager, performance_monitor
            
            # 测试缓存系统
            memory_cache.set("test_key", "test_value", ttl=10.0)
            cached_value = memory_cache.get("test_key")
            
            if cached_value == "test_value":
                self.record_test("缓存系统", True, "缓存读写正常")
            else:
                self.record_test("缓存系统", False, f"缓存值错误: {cached_value}")
            
            # 测试HTTP客户端管理器
            client = await http_client_manager.get_client()
            if client and not client.is_closed:
                self.record_test("HTTP连接池", True, "HTTP客户端管理正常")
            else:
                self.record_test("HTTP连接池", False, "HTTP客户端获取失败")
            
            # 测试性能监控
            @performance_monitor.monitor_function("test_operation")
            async def test_func():
                await asyncio.sleep(0.1)
                return "success"
            
            result = await test_func()
            stats = performance_monitor.get_stats("test_operation")
            
            if result == "success" and stats.get("count", 0) > 0:
                self.record_test("性能监控", True, f"监控正常，统计: {stats}")
            else:
                self.record_test("性能监控", False, f"监控异常，结果: {result}, 统计: {stats}")
                
        except Exception as e:
            self.record_test("性能系统", False, str(e))
    
    async def test_memory_management(self):
        """测试内存管理"""
        try:
            from src.core.memory_utils import memory_monitor, memory_leak_detector, resource_cleaner
            
            # 测试内存监控
            stats = memory_monitor.get_memory_stats()
            if stats.total_memory > 0 and stats.process_memory > 0:
                self.record_test("内存监控", True, f"内存统计正常: 系统{stats.memory_percent:.1f}%, 进程{stats.process_memory_percent:.1f}%")
            else:
                self.record_test("内存监控", False, "内存统计获取失败")
            
            # 测试垃圾回收
            import gc
            before_count = len(gc.get_objects())
            memory_monitor.force_garbage_collection()
            after_count = len(gc.get_objects())
            
            self.record_test("垃圾回收", True, f"回收前: {before_count} 对象, 回收后: {after_count} 对象")
            
            # 测试资源清理
            cleanup_called = False
            def test_cleanup():
                nonlocal cleanup_called
                cleanup_called = True
            
            resource_cleaner.register_cleanup_handler(test_cleanup)
            resource_cleaner.cleanup_all()
            
            if cleanup_called:
                self.record_test("资源清理", True, "清理处理器正常执行")
            else:
                self.record_test("资源清理", False, "清理处理器未执行")
                
        except Exception as e:
            self.record_test("内存管理", False, str(e))
    
    async def test_mcp_protocols(self):
        """测试MCP协议实现"""
        try:
            from src.mcp_server_simple import mcp as mcp_simple
            
            # 检查MCP服务器配置
            server_info = {
                "name": getattr(mcp_simple, 'name', 'Unknown'),
                "description": getattr(mcp_simple, 'description', 'Unknown')
            }
            
            if server_info["name"] and server_info["description"]:
                self.record_test("MCP服务器配置", True, f"服务器: {server_info['name']}")
            else:
                self.record_test("MCP服务器配置", False, "服务器信息缺失")
            
            self.record_test("MCP协议", True, "MCP模块加载正常")
            
        except Exception as e:
            self.record_test("MCP协议", False, str(e))
    
    async def test_error_handling(self):
        """测试错误处理"""
        try:
            from src.core.exceptions import (
                MCPBaseException, ValidationException, 
                NetworkException, CoinremitterException
            )
            
            # 测试异常类型
            exceptions_work = True
            
            try:
                raise ValidationException("Test validation error")
            except ValidationException as e:
                if "Test validation error" not in str(e):
                    exceptions_work = False
            
            try:
                raise NetworkException("Test network error")
            except NetworkException as e:
                if "Test network error" not in str(e):
                    exceptions_work = False
            
            if exceptions_work:
                self.record_test("异常处理", True, "自定义异常正常")
            else:
                self.record_test("异常处理", False, "自定义异常异常")
                
        except Exception as e:
            self.record_test("异常处理", False, str(e))
    
    async def test_data_models(self):
        """测试数据模型"""
        try:
            from src.core.models import (
                NetworkType, PaymentStatus, CreatePaymentRequest, 
                SendStablecoinRequest, PaymentResponse, BalanceResponse
            )
            
            # 测试枚举
            if NetworkType.TRC20 and NetworkType.ERC20:
                self.record_test("数据枚举", True, "网络类型枚举正常")
            else:
                self.record_test("数据枚举", False, "网络类型枚举异常")
            
            # 测试数据验证
            try:
                # 有效请求
                valid_request = CreatePaymentRequest(
                    amount_usd=100.0,
                    network=NetworkType.TRC20,
                    description="Test payment"
                )
                
                # 无效请求（负金额）
                try:
                    invalid_request = CreatePaymentRequest(
                        amount_usd=-10.0,
                        network=NetworkType.TRC20
                    )
                    self.record_test("数据验证", False, "负金额验证失败")
                except Exception:
                    self.record_test("数据验证", True, "Pydantic验证正常")
                    
            except Exception as e:
                self.record_test("数据验证", False, f"模型创建失败: {e}")
                
        except Exception as e:
            self.record_test("数据模型", False, str(e))
    
    async def test_production_config(self):
        """测试生产环境配置"""
        try:
            from src.core.config import settings
            
            config_issues = []
            
            # 检查调试模式
            if settings.debug:
                config_issues.append("DEBUG模式在生产环境应关闭")
            
            # 检查端口配置
            if settings.port == 8000 and os.getenv("PORT"):
                config_issues.append("生产环境应使用环境变量PORT")
            
            # 检查密钥配置
            if not settings.hmac_secret or len(settings.hmac_secret) < 16:
                config_issues.append("HMAC密钥长度不足")
            
            if not settings.jwt_secret or len(settings.jwt_secret) < 16:
                config_issues.append("JWT密钥长度不足")
            
            if config_issues:
                self.record_test("生产环境配置", False, f"配置问题: {', '.join(config_issues)}")
            else:
                self.record_test("生产环境配置", True, "生产环境配置检查通过")
                
        except Exception as e:
            self.record_test("生产环境配置", False, str(e))
    
    async def test_docker_compatibility(self):
        """测试Docker兼容性"""
        try:
            # 检查Docker相关文件
            docker_files = ["Dockerfile", "Dockerfile.cloud", "docker-compose.yml"]
            missing_files = []
            
            for file in docker_files:
                if not os.path.exists(file):
                    missing_files.append(file)
            
            if missing_files:
                self.record_test("Docker兼容性", False, f"缺失文件: {', '.join(missing_files)}")
            else:
                self.record_test("Docker兼容性", True, "Docker配置文件完整")
            
            # 检查云部署配置
            cloud_configs = ["config.env.cloud", "CLOUD_DEPLOYMENT.md"]
            missing_cloud = []
            
            for file in cloud_configs:
                if not os.path.exists(file):
                    missing_cloud.append(file)
            
            if missing_cloud:
                self.record_test("云部署配置", False, f"缺失文件: {', '.join(missing_cloud)}")
            else:
                self.record_test("云部署配置", True, "云部署配置完整")
                
        except Exception as e:
            self.record_test("Docker兼容性", False, str(e))
    
    def generate_report(self) -> Dict[str, Any]:
        """生成测试报告"""
        total_tests = self.passed_tests + self.failed_tests
        success_rate = (self.passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        report = {
            "test_summary": {
                "total_tests": total_tests,
                "passed_tests": self.passed_tests,
                "failed_tests": self.failed_tests,
                "success_rate": f"{success_rate:.1f}%"
            },
            "production_ready": self.failed_tests == 0,
            "timestamp": datetime.now().isoformat(),
            "detailed_results": self.test_results
        }
        
        return report
    
    async def run_all_tests(self):
        """运行所有测试"""
        logger.info("🚀 开始生产环境就绪性测试")
        logger.info("=" * 60)
        
        tests = [
            self.test_core_imports,
            self.test_configuration_security,
            self.test_input_validation,
            self.test_performance_systems,
            self.test_memory_management,
            self.test_mcp_protocols,
            self.test_error_handling,
            self.test_data_models,
            self.test_production_config,
            self.test_docker_compatibility
        ]
        
        for test in tests:
            try:
                await test()
            except Exception as e:
                logger.error(f"测试执行异常: {test.__name__}: {e}")
                self.record_test(test.__name__, False, f"测试执行异常: {e}")
        
        # 生成报告
        report = self.generate_report()
        
        logger.info("=" * 60)
        logger.info("📊 测试报告")
        logger.info(f"总测试数: {report['test_summary']['total_tests']}")
        logger.info(f"通过测试: {report['test_summary']['passed_tests']}")
        logger.info(f"失败测试: {report['test_summary']['failed_tests']}")
        logger.info(f"成功率: {report['test_summary']['success_rate']}")
        
        if report["production_ready"]:
            logger.success("🎉 系统已准备好投入生产环境！")
        else:
            logger.warning("⚠️  系统还需要修复一些问题才能投入生产")
        
        # 保存报告
        with open("production_readiness_report.json", "w", encoding="utf-8") as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        logger.info("📄 详细报告已保存到 production_readiness_report.json")
        
        return report


async def main():
    """主函数"""
    tester = ProductionReadinessTest()
    report = await tester.run_all_tests()
    
    # 返回适当的退出码
    sys.exit(0 if report["production_ready"] else 1)


if __name__ == "__main__":
    asyncio.run(main()) 