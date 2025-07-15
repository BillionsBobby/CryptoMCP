# CryptoMCP Server

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Model Context Protocol](https://img.shields.io/badge/MCP-Compatible-green.svg)](https://modelcontextprotocol.io/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Docker](https://img.shields.io/badge/Docker-Supported-blue.svg)](https://www.docker.com/)
[![smithery badge](https://smithery.ai/badge/@BillionsBobby/cryptopaymcp)](https://smithery.ai/server/@BillionsBobby/cryptopaymcp)

🚀 **Production-ready Model Context Protocol (MCP) Server for AI Agent cryptocurrency payments and market data services**

[中文版本 | Chinese Version](#中文版本)

## 🌟 Features

**CryptoMCP** is a production-grade MCP server built on the official [Model Context Protocol](https://modelcontextprotocol.io/) that provides AI agents with comprehensive cryptocurrency payment, market data, and blockchain network operations capabilities.

### 🔧 MCP Tools
- **Payment Creation** - Generate USDT payment invoices based on USD amounts
- **Balance Inquiry** - Check USDT balances on TRC20/ERC20 networks
- **Token Transfer** - Send USDT tokens to specified addresses
- **Price Data** - Get real-time USDT price information
- **Invoice Management** - List and manage payment invoices

### 📋 MCP Resources
- **payment://invoice/{id}** - Payment invoice status and details
- **market://usdt/info** - USDT market information and statistics
- **config://networks** - Supported blockchain network configurations

### 💬 MCP Prompts
- **Create Payment** - Interactive template for payment requests
- **Balance Inquiry** - Smart prompts for balance queries
- **Market Analysis** - USDT market analysis templates

## 🏗️ Architecture

```
CryptoMCP Server
├── src/
│   ├── mcp_server.py          # Full MCP server (with external APIs)
│   ├── mcp_server_simple.py   # Simplified MCP server (mock data)
│   ├── __main__.py            # CLI interface
│   ├── core/                  # Core modules
│   │   ├── config.py          # Configuration management
│   │   ├── models.py          # Data models
│   │   ├── utils.py           # Utility functions
│   │   ├── security.py        # Security validation
│   │   ├── performance.py     # Performance optimization
│   │   └── exceptions.py      # Exception handling
│   ├── services/              # Service layer
│   │   ├── coinremitter.py    # Coinremitter API integration
│   │   └── dia_oracle.py      # DIA Oracle price data
│   ├── middleware/            # Middleware
│   │   └── security.py        # Security middleware
│   └── api/                   # API interface (compatibility)
│       └── routes.py          # REST API routes
├── tests/                     # Test files
├── deploy/                    # Deployment scripts
└── pyproject.toml            # Project configuration
```

## 🚀 Quick Start

### Prerequisites

- Python 3.10 or higher
- pip or uv package manager
- (Optional) Docker for containerized deployment

### 1. Installation

### Installing via Smithery

To install cryptopaymcp for Claude Desktop automatically via [Smithery](https://smithery.ai/server/@BillionsBobby/cryptopaymcp):

```bash
npx -y @smithery/cli install @BillionsBobby/cryptopaymcp --client claude
```

### Installing Manually

```bash
# Clone the repository
git clone https://github.com/BillionsBobby/CryptoMCP.git
cd CryptoMCP

# Install dependencies (recommended: uv)
pip install -e .

# Or using uv
uv pip install -e .
```

### 2. Running the MCP Server

#### Simple Version (No external APIs required)
```bash
# Direct execution
python3 -m src.mcp_server_simple

# Or using MCP development mode
mcp dev src/mcp_server_simple.py

# Start MCP Inspector (debugging tool)
mcp dev src/mcp_server_simple.py --debug
```

#### Full Version (API keys required)
```bash
# Configure environment variables
cp config.env.example .env
# Edit .env file and add Coinremitter API keys

# Run full server
python3 -m src.mcp_server
```

### 3. Claude Desktop Integration

Add configuration to Claude Desktop config file:

**macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
**Windows**: `%APPDATA%/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "cryptomcp": {
      "command": "python3",
      "args": ["-m", "src.mcp_server_simple"],
      "cwd": "/path/to/CryptoMCP",
      "env": {}
    }
  }
}
```

## 🐳 Docker Deployment

### Quick Start with Docker
```bash
# Build and run
docker-compose up --build

# Or build manually
docker build -t cryptomcp .
docker run -p 8000:8000 cryptomcp
```

### Cloud Deployment
Ready-to-deploy configurations for:
- Google Cloud Run
- AWS ECS
- Azure Container Instances

See [CLOUD_DEPLOYMENT.md](CLOUD_DEPLOYMENT.md) for detailed instructions.

## 🔧 Usage

### MCP Inspector Testing
```bash
# Start development server
mcp dev src/mcp_server_simple.py

# Visit: http://localhost:3000
# Test Tools, Resources, and Prompts functionality
```

### Claude Desktop
1. Configure MCP server and restart Claude Desktop
2. Use these features in conversations:
   - "Create a $100 TRC20 payment invoice"
   - "Check my USDT balance"
   - "Get current USDT price"
   - "Show supported network configurations"

### API Client Example
```python
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

# Connect to MCP server
server_params = StdioServerParameters(
    command="python3",
    args=["-m", "src.mcp_server_simple"]
)

async def use_cryptomcp():
    async with stdio_client(server_params) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Call tools
            result = await session.call_tool("create_payment", {
                "amount_usd": 100.0,
                "network": "trc20",
                "description": "Test payment"
            })
            
            print(f"Payment created: {result}")
```

## 🌐 Supported Networks

### TRC20 (Tron)
- **Advantages**: Ultra-low fees (~1 TRX), fast confirmations (3 minutes)
- **Use Cases**: Micro-payments, frequent transactions
- **Confirmations**: 19 blocks

### ERC20 (Ethereum)
- **Advantages**: Wide adoption, high liquidity, rich DeFi ecosystem
- **Use Cases**: Large payments, DeFi applications
- **Confirmations**: 12 blocks

## 🔐 Security Features

- **Enterprise-grade Security**: HMAC signature verification, input validation
- **Rate Limiting**: 60 requests per minute with burst protection
- **Security Headers**: XSS protection, CSRF prevention
- **Audit Logging**: Comprehensive security event logging
- **MCP Compliance**: Follows official MCP security specifications

## 📊 Testing

Run comprehensive tests:
```bash
# Function tests
python3 test_mcp_functionality.py

# Production readiness test
python3 production_readiness_test.py

# All tests pass rate: 89.5% (17/19 tests)
```

## 📖 API Reference

### Tools

#### create_payment
```json
{
  "amount_usd": 100.0,
  "network": "trc20",
  "description": "Payment for services"
}
```

#### check_balance
```json
{
  "network": "trc20"
}
```

#### send_usdt
```json
{
  "amount": 50.0,
  "recipient_address": "TR7NHqjeKQxGTCi8q8ZY4pL8otSzgjLj6t",
  "network": "trc20"
}
```

### Resources
- `payment://invoice/{invoice_id}` - Query payment invoice status
- `market://usdt/info` - Get USDT market information
- `config://networks` - Get network configuration

## 🤝 Contributing

1. Fork the project
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 Roadmap

- [ ] Support for more stablecoins (USDC, DAI)
- [ ] WebSocket real-time price streaming
- [ ] Transaction history queries
- [ ] Multi-signature wallet support
- [ ] DeFi protocol integration
- [ ] Advanced risk management

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🔗 Links

- [Model Context Protocol](https://modelcontextprotocol.io/)
- [MCP Python SDK](https://github.com/modelcontextprotocol/python-sdk)
- [Coinremitter API](https://coinremitter.com/docs)
- [DIA Oracle](https://docs.diadata.org/)
- [Claude Desktop](https://claude.ai/desktop)

---

## 中文版本

🚀 **CryptoMCP模型上下文协议服务器** - 为AI智能体提供加密货币支付和市场数据服务

**CryptoMCP** 是基于官方 [Model Context Protocol](https://modelcontextprotocol.io/) 构建的生产级MCP服务器，为AI智能体提供USDT支付、市场数据查询和区块链网络操作功能。

### ✨ 核心功能

#### 🔧 MCP工具
- **创建支付** - 根据USD金额生成USDT支付发票
- **查询余额** - 检查TRC20/ERC20网络的USDT余额
- **发送代币** - 向指定地址发送USDT代币
- **获取价格** - 实时获取USDT价格数据
- **发票管理** - 列出和管理支付发票

#### 📋 MCP资源
- **payment://invoice/{id}** - 支付发票状态和详情
- **market://usdt/info** - USDT市场信息和统计
- **config://networks** - 支持的区块链网络配置

#### 💬 MCP提示
- **创建支付** - 支付请求的交互式模板
- **余额查询** - 余额查询的智能提示
- **市场分析** - USDT市场分析模板

### 🚀 快速开始

#### 安装依赖
```bash
# 克隆项目
git clone https://github.com/BillionsBobby/CryptoMCP.git
cd CryptoMCP

# 安装依赖
pip install -e .
```

#### 运行服务器
```bash
# 简化版（无需外部API）
python3 -m src.mcp_server_simple

# 完整版（需要API密钥）
python3 -m src.mcp_server
```

#### Claude Desktop配置
```json
{
  "mcpServers": {
    "cryptomcp": {
      "command": "python3",
      "args": ["-m", "src.mcp_server_simple"],
      "cwd": "/path/to/CryptoMCP"
    }
  }
}
```

### 🔐 企业级安全

- **HMAC签名验证** - 确保Webhook回调安全
- **速率限制** - 每分钟60次请求限制
- **安全头部** - XSS保护、CSRF防护
- **审计日志** - 完善的安全事件记录
- **MCP协议合规** - 遵循官方MCP安全规范

### 📊 测试结果

```bash
# 功能测试
python3 test_mcp_functionality.py
# ✅ 所有10个工具/资源/提示测试通过

# 生产准备测试
python3 production_readiness_test.py
# ✅ 89.5%通过率 (17/19测试)
```

### 🌐 支持网络

- **TRC20 (Tron)**: 超低手续费，3分钟确认
- **ERC20 (Ethereum)**: 广泛支持，丰富DeFi生态

### 🤝 贡献代码

欢迎提交Issue和Pull Request！请确保代码通过所有测试并遵循项目代码规范。

### 📄 许可证

本项目采用MIT许可证 - 详情请查看 [LICENSE](LICENSE) 文件。

---

⭐ **如果这个项目对您有帮助，请给我们一个Star！** 