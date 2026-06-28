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

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from sse_starlette.sse import EventSourceResponse

from app.database import Database
from app.services import ConfigService
from app.api.routes import router, init_services

import time
import random
import asyncio
from typing import AsyncGenerator


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
    应用启动时初始化数据库和服务，并自动生成配置文件
    """
    print("Avalon Tunnel API 服务器启动中...")
    
    # 基础目录
    base_dir = os.getenv('BASE_DIR', '/app/config')
    
    # 初始化数据库
    db_path = f"{base_dir}/data/avalon.db"
    db = Database(db_path)
    print(f"  [Database] 数据库已连接: {db_path}")
    
    # 将数据库实例存入 App State，以便认证拦截器等处使用
    app.state.db = db
    
    # 从数据库获取 Domain，若没有则回退到环境变量或默认值
    db_domain = db.get_setting('domain')
    if db_domain:
        domain = db_domain
    else:
        domain = os.getenv('DOMAIN', 'your-domain.com')
        db.set_setting('domain', domain, '域名配置')
    
    # 初始化配置服务
    config_service = ConfigService(base_dir)
    print(f"  [Service] 配置服务已初始化")
    
    # 启动时自动生成并同步一次配置文件，保证只要有数据库在就能瞬间重建运行环境
    try:
        print("  [Config] 正在自动生成/同步配置文件...")
        users = db.get_all_users(enabled_only=True)
        v2ray_port = int(db.get_setting('v2ray_port') or 10000)
        config_service.sync_all_configs(domain, users, v2ray_port, db)
        print("  [Config] 配置文件已自动生成/同步成功")
    except Exception as e:
        print(f"  [Warning] 启动自动同步配置失败: {e}")
    
    # 初始化 API 路由服务
    init_services(db, config_service, domain)
    print(f"  [API] API 路由已初始化")
    print(f"  [API] 域名: {domain}")
    print()
    print("=" * 70)
    print("Avalon Tunnel API 服务器已启动")
    print("=" * 70)
    print(f"  [Doc] API 文档: http://0.0.0.0:8000/docs")
    print(f"  [Health] 健康检查: http://0.0.0.0:8000/api/health")
    print("=" * 70)


# 关闭事件
@app.on_event("shutdown")
async def shutdown_event():
    """
    应用关闭时的清理工作
    """
    print("Avalon Tunnel API 服务器正在关闭...")


# 注册 API 路由
app.include_router(router)


# ==================== 伪装流量系统 ====================

# 配置路径
BASE_DIR = Path(os.getenv('BASE_DIR', '.')).resolve()
PUBLIC_DIR = Path(__file__).parent.parent / 'public'
VIDEO_FILE = PUBLIC_DIR / 'video.mp4'
VIDEO_FILE_2 = PUBLIC_DIR / 'video2.mp4'  # 第二个视频
CHAT_CORPUS_FILE = PUBLIC_DIR / 'chat_corpus.txt'

# 加载聊天语料库
CHAT_MESSAGES = [
    "Hey, anyone online?",
    "Just finished watching that video",
    "This platform is pretty cool",
    "Great content today!",
    "Thanks for the invite",
]

if CHAT_CORPUS_FILE.exists():
    try:
        with open(CHAT_CORPUS_FILE, 'r', encoding='utf-8') as f:
            custom_messages = [line.strip() for line in f if line.strip()]
            if custom_messages:
                CHAT_MESSAGES = custom_messages
    except Exception:
        pass


# 固定的伪装路径
DECOY_PATH = "MwH1HvttOawqljoOZFIYImPi2adY0CLG"


@app.get("/stream/{segment_id}")
async def serve_video_segment(segment_id: str, request: Request):
    """
    伪装视频流服务 - 路径格式与 VPN 流量完全一致
    
    URL 格式: /stream/<32位随机字符>
    - 如果 segment_id 匹配用户的 secret_path，Caddy 会转发给 V2Ray（VPN 流量）
    - 如果不匹配，会到达这里，返回视频流（伪装流量）
    
    这样 VPN 流量和伪装流量的 URL 格式完全一致，无法区分！
    """
    if not VIDEO_FILE.exists():
        return Response(content="Video not found", status_code=404)
    
    file_size = VIDEO_FILE.stat().st_size
    range_header = request.headers.get('range')
    
    if range_header:
        # 处理 Range 请求
        range_match = range_header.replace('bytes=', '').split('-')
        start = int(range_match[0]) if range_match[0] else 0
        end = int(range_match[1]) if len(range_match) > 1 and range_match[1] else file_size - 1
        
        def iterfile():
            with open(VIDEO_FILE, 'rb') as f:
                f.seek(start)
                remaining = end - start + 1
                chunk_size = 64 * 1024  # 64KB chunks
                while remaining > 0:
                    chunk = f.read(min(chunk_size, remaining))
                    if not chunk:
                        break
                    remaining -= len(chunk)
                    yield chunk
        
        return StreamingResponse(
            iterfile(),
            media_type="video/mp4",
            status_code=206,
            headers={
                "Content-Range": f"bytes {start}-{end}/{file_size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(end - start + 1),
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )
    else:
        # 完整文件请求
        def iterfile():
            with open(VIDEO_FILE, 'rb') as f:
                chunk_size = 64 * 1024
                while True:
                    chunk = f.read(chunk_size)
                    if not chunk:
                        break
                    yield chunk
        
        return StreamingResponse(
            iterfile(),
            media_type="video/mp4",
            headers={
                "Accept-Ranges": "bytes",
                "Content-Length": str(file_size),
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            }
        )


@app.get("/{path:path}")
async def unified_decoy_endpoint(path: str = "", request: Request = None):
    """
    统一的伪装端点 - 只有一个路径，无参数
    
    - / : 返回主页 (decoy.html)
    - /MwH1HvttOawqljoOZFIYImPi2adY0CLG : 返回 SSE 流（聊天消息）
    
    注意：与真实 VPN 流量保持一致，不使用任何 query 参数
    """
    # API 路径已被 router 处理，不会到这里
    
    # 根路径 - 返回主页
    if not path or path == "":
        decoy_html = PUBLIC_DIR / 'decoy.html'
        if decoy_html.exists():
            return FileResponse(decoy_html)
        return Response(content="Not Found", status_code=404)
    
    # 检查是否是固定的伪装路径
    if path == DECOY_PATH:
        # 检查是否是 SSE 请求（通过 Accept header）
        accept = request.headers.get('accept', '') if request else ''
        
        if 'text/event-stream' in accept:
            # SSE 请求 - 返回聊天流（长间隔）
            async def generate_chat_events():
                import json
                users = ['Alice', 'Bob', 'Charlie', 'Diana']
                
                while True:
                    # 随机间隔 1-300 秒（1-5 分钟）
                    wait_seconds = random.randint(1, 300)
                    await asyncio.sleep(wait_seconds)
                    
                    # SSE 格式：必须是 data 字段
                    event_data = {
                        "user": random.choice(users),
                        "message": random.choice(CHAT_MESSAGES),
                        "timestamp": int(time.time())
                    }
                    yield {"data": json.dumps(event_data)}
            
            return EventSourceResponse(generate_chat_events())
        else:
            # 普通 HTTP 请求 - 返回 HTML 页面
            decoy_html = PUBLIC_DIR / 'decoy.html'
            if decoy_html.exists():
                return FileResponse(decoy_html)
    
    # 其他路径，返回 404
    return Response(content="Not Found", status_code=404)


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
