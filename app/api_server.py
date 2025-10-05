#!/usr/bin/env python3
"""
Avalon Tunnel - API 服务器入口
持久运行的 FastAPI 服务器，提供用户管理和配置管理 API
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.database import Database
from app.services import ConfigService
from app.api.routes import router, init_services


# 创建 FastAPI 应用
app = FastAPI(
    title="Avalon Tunnel API",
    description="用户管理和配置管理 REST API",
    version="2.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# 配置 CORS（允许跨域请求）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 生产环境应该限制具体域名
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 启动事件：初始化服务
@app.on_event("startup")
async def startup_event():
    """
    应用启动时初始化数据库和服务
    """
    print("🚀 Avalon Tunnel API 服务器启动中...")
    
    # 读取环境变量
    domain = os.getenv('DOMAIN', 'your-domain.com')
    base_dir = os.getenv('BASE_DIR', '/app/config')
    
    # 初始化数据库
    db_path = f"{base_dir}/data/avalon.db"
    db = Database(db_path)
    print(f"  ✅ 数据库已连接: {db_path}")
    
    # 初始化配置服务
    config_service = ConfigService(base_dir)
    print(f"  ✅ 配置服务已初始化")
    
    # 初始化 API 路由服务
    init_services(db, config_service, domain)
    print(f"  ✅ API 路由已初始化")
    print(f"  📍 域名: {domain}")
    print()
    print("=" * 70)
    print("🎉 Avalon Tunnel API 服务器已启动")
    print("=" * 70)
    print(f"  📖 API 文档: http://0.0.0.0:8000/docs")
    print(f"  🔗 健康检查: http://0.0.0.0:8000/api/health")
    print("=" * 70)


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭时的清理工作
    """
    print("🛑 Avalon Tunnel API 服务器正在关闭...")


# 注册路由
app.include_router(router)


# 根路径
@app.get("/")
async def root():
    """
    根路径，返回 API 信息
    """
    return {
        "service": "Avalon Tunnel API",
        "version": "2.0.0",
        "docs": "/docs",
        "health": "/api/health"
    }


# 全局异常处理
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """
    全局异常处理器
    """
    return JSONResponse(
        status_code=500,
        content={
            "success": False,
            "message": "服务器内部错误",
            "detail": str(exc)
        }
    )


if __name__ == "__main__":
    import uvicorn
    
    # 运行服务器
    uvicorn.run(
        "api_server:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 生产环境关闭自动重载
        log_level="info"
    )
