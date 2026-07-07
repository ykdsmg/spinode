"""fmshop 多电商平台数据同步系统。

包结构:
- core:     全局基础 (settings/logging/exceptions/converters)
- http:     统一 HTTP 客户端 (异步 aiohttp + 同步 requests)
- db:       aiomysql 连接池与异步通用仓储
- platform: 平台抽象基类与注册表
- platforms: 各平台具体实现 (falabella / mercado)
"""

__version__ = "2.0.0"
