"""
API 认证模块
使用 Bearer Token 进行简单认证
"""

import os
from fastapi import HTTPException, Security
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

# 从环境变量读取 API 密钥
API_SECRET = os.getenv('API_SECRET', '')

# HTTP Bearer 认证
security = HTTPBearer()


def verify_api_token(credentials: HTTPAuthorizationCredentials = Security(security)) -> bool:
    """
    验证 API Token
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        bool: 验证成功返回 True
        
    Raises:
        HTTPException: 验证失败抛出 401 错误
    """
    if not API_SECRET:
        raise HTTPException(
            status_code=500,
            detail="API_SECRET not configured. Please set API_SECRET in .env file."
        )
    
    if credentials.credentials != API_SECRET:
        raise HTTPException(
            status_code=401,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return True
