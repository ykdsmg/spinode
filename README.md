# Spinode v2.0

多电商平台数据同步系统 - REST API 服务

## 📋 项目简介

Spinode 是一个基于 FastAPI 构建的多电商平台数据同步系统，支持从多个拉丁美洲电商平台（Falabella、Mercado Libre、Paris）同步订单、商品、库存、账单和广告数据到 MySQL 数据库。

## ✨ 功能特性

### 支持的平台
- **Falabella** - 智利领先的零售电商平台
- **Mercado Libre** - 拉丁美洲最大的电子商务平台
- **Paris (Cencosud)** - 智利大型零售集团的电商平台

### 数据同步功能
- 📦 **订单同步** - 获取订单详情、订单项、支付信息、物流状态
- 🛍️ **商品同步** - 商品信息、图片、变体、属性
- 📊 **库存同步** - 仓库库存、Fulfillment 库存
- 💰 **账单同步** - 账单周期、费用明细（ML/MP/FLEX/FULL）
- 📢 **广告同步** - 广告主、广告组、广告详情及每日指标

### 技术特点
- 🚀 **高性能异步架构** - 基于 FastAPI + uvicorn 的异步 REST API
- 🔄 **智能重试机制** - 指数退避重试策略，提高数据同步可靠性
- 🌐 **TLS 指纹模拟** - 使用 curl_cffi 模拟真实浏览器 TLS 指纹，避免反爬虫检测
- ⚡ **并发请求优化** - 使用 asyncio.gather 实现并行 API 调用
- 🔐 **OAuth2 自动刷新** - Mercado 和 Paris 平台的令牌自动续期
- 📈 **速率限制** - 支持 QPM（每分钟查询数）限制，遵守 API 频率限制

## 🏗️ 项目结构

```
spinode/
├── main.py                    # 应用入口 (uvicorn 启动器)
├── config.json                # 数据库连接配置
├── requirements.txt           # Python 依赖
├── README.md                  # 项目文档
├── .gitignore                 # Git 忽略规则
└── app/                       # 主应用包
    ├── __init__.py            # 版本信息 (v2.0.0)
    ├── main.py                # FastAPI 应用实例 + 生命周期管理
    ├── config.py              # 店铺配置加载器
    ├── api/                   # REST API 层
    │   ├── schemas.py         # Pydantic 数据模型
    │   └── routers/           # API 路由
    │       ├── falabella.py   # Falabella 路由 (9 个端点)
    │       ├── mercado.py     # Mercado Libre 路由 (26 个端点)
    │       └── paris.py       # Paris 路由 (2 个端点)
    ├── core/                  # 核心工具模块
    │   ├── converters.py      # 数据转换工具
    │   ├── logging.py         # 日志配置
    │   └── settings.py        # 配置管理
    ├── db/                    # 数据库层
    │   ├── pool.py            # aiomysql 连接池
    │   └── manager.py         # 数据库操作管理器
    ├── platform/              # 平台抽象层
    │   ├── FalabellaShop.py   # Falabella 店铺实现
    │   ├── MercadoShop.py     # Mercado Libre 店铺实现
    │   └── ParisShop.py       # Paris 店铺实现
    └── resources/             # 业务逻辑层
        ├── falabella/         # Falabella 资源 (订单/商品/库存)
        ├── mercado/           # Mercado Libre 资源 (订单/商品/库存/账单/广告)
        └── paris/             # Paris 资源 (订单)
```

## 🚀 快速开始

### 环境要求
- Python 3.11+
- MySQL 数据库

### 安装步骤

1. **克隆项目**
   ```bash
   git clone <repository-url>
   cd spinode
   ```

2. **创建虚拟环境**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # 或
   venv\Scripts\activate     # Windows
   ```

3. **安装依赖**
   ```bash
   pip install -r requirements.txt
   ```

4. **配置数据库**
   编辑 `config.json` 文件，填入数据库连接信息：
   ```json
   {
     "host": "your-database-host",
     "port": 3306,
     "user": "your-username",
     "password": "your-password",
     "database": "your-database",
     "charset": "utf8mb4",
     "autocommit": false,
     "pool_size": 10
   }
   ```

5. **启动服务**
   ```bash
   # 开发模式 (热重载)
   python main.py --reload
   
   # 生产模式
   python main.py --host 0.0.0.0 --port 8000
   ```

### 使用 uvicorn 直接启动
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## 📚 API 文档

启动服务后，访问以下地址查看 API 文档：

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

### 主要 API 端点

#### Falabella 平台 (`/falabella/`)
- `POST /falabella/orders/sync` - 同步订单数据
- `GET /falabella/order/{order_id}` - 获取单个订单详情
- `GET /falabella/orders/search` - 搜索订单
- `POST /falabella/products/sync` - 同步商品数据
- `GET /falabella/products/search` - 搜索商品
- `POST /falabella/stocks/sync` - 同步库存数据
- `GET /falabella/stocks/search` - 搜索库存

#### Mercado Libre 平台 (`/mercado/`)
- `POST /mercado/orders/sync` - 同步订单数据
- `GET /mercado/order/{order_id}` - 获取单个订单详情
- `POST /mercado/product/item/{item_id}/sync` - 同步商品数据
- `POST /mercado/user_product/stocks/sync` - 同步库存数据
- `POST /mercado/billing/Periods/billing/sync` - 同步账单数据
- `POST /mercado/ads/advertisers/sync` - 同步广告数据
- 还有更多端点...

#### Paris 平台 (`/paris/`)
- `POST /paris/shop/orders/sync` - 同步订单数据
- `GET /paris/shop/{seller_id}/order/search` - 搜索订单

## 🔧 配置说明

### 应用配置
- **并发连接数**: 200 个最大并发 HTTP 连接
- **请求超时**: 60 秒
- **重试策略**: 5 次重试，指数退避，初始延迟 1 秒
- **数据库连接池**: 最小 2 个连接，最大 10 个连接，1 小时回收

### 平台认证
- **Falabella**: HMAC-SHA256 签名认证
- **Mercado Libre**: OAuth2 令牌认证 (自动刷新)
- **Paris**: API Key 认证 (令牌自动续期)

## 📁 日志管理

日志文件位于 `logs/app.log`，支持：
- 按天自动轮转
- 保留最近 7 天的日志
- 同时输出到控制台和文件

## 🤝 贡献指南

1. Fork 项目
2. 创建功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 创建 Pull Request

## 📄 许可证

本项目使用 [MIT License](LICENSE) 许可证。

## 📞 联系方式

- 项目地址: [GitHub Repository](https://github.com/your-username/spinode)
- 问题反馈: [Issues](https://github.com/your-username/spinode/issues)

## 🙏 致谢

- [FastAPI](https://fastapi.tiangolo.com/) - 现代高性能 Web 框架
- [curl_cffi](https://github.com/lwthiker/curl-cffi) - 支持 TLS 指纹模拟的 HTTP 客户端
- [aiomysql](https://github.com/aio-libs/aiomysql) - 异步 MySQL 驱动
- [Pydantic](https://docs.pydantic.dev/) - 数据验证库
