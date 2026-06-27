"""
API 认证模块
使用 Bearer Token 进行简单认证
"""

import os
from fastapi import HTTPException, Security, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# HTTP Bearer 认证
security = HTTPBearer()


def verify_api_token(request: Request, credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """
    验证 API Token
    
    Args:
        request: FastAPI Request 对象，用于获取数据库实例
        credentials: HTTP Authorization credentials
        
    Returns:
        bool: 验证成功返回 True
        
    Raises:
        HTTPException: 验证失败抛出 401 错误
    """
    # 从数据库获取 api_secret 设置
    try:
        db = request.app.state.db
        api_secret = db.get_setting('api_secret')
    except Exception:
        api_secret = None
        
    # 如果数据库中没有，回退到环境变量
    if not api_secret:
        api_secret = os.getenv('API_SECRET', '')
        
    if not api_secret:
        raise HTTPException(
            status_code=500,
            detail="API_SECRET not configured. Please configure api_secret in database or set API_SECRET environment variable."
        )
    
    if credentials.credentials != api_secret:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True
