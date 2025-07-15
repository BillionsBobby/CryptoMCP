#!/usr/bin/env python3
"""
MCP Crypto Payment 项目验证脚本
验证项目基本结构和模块导入是否正常
"""

import sys
import traceback
from pathlib import Path

def test_basic_imports():
    """测试基本模块导入"""
    print("🔍 测试基本模块导入...")
    
    try:
        # 测试核心模块
        from src.core.config import Settings
        from src.core.models import NetworkType, PaymentStatus
        from src.core.utils import validate_usdt_amount, generate_secure_token
        from src.core.exceptions import MCPBaseException
        print("✅ 核心模块导入成功")
        
        # 测试数据模型
        network = NetworkType.TRC20
        status = PaymentStatus.PENDING
        assert network == "trc20"
        assert status == "pending"
        print("✅ 数据模型工作正常")
        
        # 测试工具函数
        assert validate_usdt_amount(10.0) == True
        assert validate_usdt_amount(-1.0) == False
        token = generate_secure_token(16)
        assert len(token) > 0
        print("✅ 工具函数工作正常")
        
        return True
    except Exception as e:
        print(f"❌ 基本模块导入失败: {e}")
        traceback.print_exc()
        return False

def test_service_structure():
    """测试服务层结构"""
    print("\n🔍 测试服务层结构...")
    
    try:
        # 测试服务类导入（不进行实际初始化）
        from src.services.dia_oracle import DIAOracleService
        from src.services.coinremitter import CoinremitterService
        print("✅ 服务类导入成功")
        
        # 检查类是否有必要的方法
        dia_service = DIAOracleService.__new__(DIAOracleService)
        assert hasattr(dia_service, 'get_usdt_price')
        assert hasattr(dia_service, 'calculate_usdt_amount')
        
        coinremitter_service = CoinremitterService.__new__(CoinremitterService)
        assert hasattr(coinremitter_service, 'create_invoice')
        assert hasattr(coinremitter_service, 'get_balance')
        print("✅ 服务类方法检查通过")
        
        return True
    except Exception as e:
        print(f"❌ 服务层测试失败: {e}")
        traceback.print_exc()
        return False

def test_agent_structure():
    """测试Agent结构"""
    print("\n🔍 测试Agent结构...")
    
    try:
        # 测试Agent模块导入（不进行实际初始化）
        from src.agent.wallet import WalletAgent, PaymentRequest, PaymentResponse
        print("✅ Agent类导入成功")
        
        # 检查消息模型
        request = PaymentRequest(
            recipient="TTest123...abc",
            amount=5.0,
            network="trc20",
            request_id="TEST_123"
        )
        assert request.amount == 5.0
        assert request.network == "trc20"
        print("✅ Agent消息模型工作正常")
        
        return True
    except Exception as e:
        print(f"❌ Agent结构测试失败: {e}")
        traceback.print_exc()
        return False

def test_api_structure():
    """测试API结构"""
    print("\n🔍 测试API结构...")
    
    try:
        from src.api.routes import router
        from src.main import app
        print("✅ API模块导入成功")
        
        # 检查路由是否注册
        assert hasattr(app, 'routes')
        assert router is not None
        print("✅ API路由结构正常")
        
        return True
    except Exception as e:
        print(f"❌ API结构测试失败: {e}")
        traceback.print_exc()
        return False

def test_project_structure():
    """测试项目结构完整性"""
    print("\n🔍 测试项目结构完整性...")
    
    required_files = [
        "src/__init__.py",
        "src/main.py",
        "src/core/__init__.py",
        "src/core/config.py",
        "src/core/models.py",
        "src/core/utils.py",
        "src/core/exceptions.py",
        "src/services/__init__.py",
        "src/services/coinremitter.py",
        "src/services/dia_oracle.py",
        "src/agent/__init__.py",
        "src/agent/wallet.py",
        "src/api/__init__.py",
        "src/api/routes.py",
        "tests/__init__.py",
        "tests/test_mcp_integration.py",
        "pyproject.toml",
        "Dockerfile",
        "docker-compose.yml",
        "README.md"
    ]
    
    missing_files = []
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_files.append(file_path)
    
    if missing_files:
        print(f"❌ 缺少以下文件: {missing_files}")
        return False
    else:
        print("✅ 所有必需文件都存在")
        return True

def main():
    """主验证函数"""
    print("🚀 MCP Crypto Payment 项目验证")
    print("=" * 50)
    
    tests = [
        test_project_structure,
        test_basic_imports,
        test_service_structure,
        test_agent_structure,
        test_api_structure,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"❌ 测试异常: {e}")
            failed += 1
    
    print("\n" + "=" * 50)
    print(f"📊 验证结果: {passed} 通过, {failed} 失败")
    
    if failed == 0:
        print("🎉 项目验证成功！MCP系统已正确构建")
        print("\n📚 下一步:")
        print("1. 配置环境变量 (复制 config.env.example 到 .env)")
        print("2. 获取Coinremitter API密钥")
        print("3. 运行: python3 -m src.main")
        print("4. 访问: http://localhost:8000/docs")
        return True
    else:
        print("❌ 项目验证失败，请检查错误信息")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 