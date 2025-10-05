#!/usr/bin/env python3
"""
Avalon Tunnel - API 数据模型
使用 Pydantic 进行请求/响应数据验证
"""

from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ==================== 请求模型 ====================

class CreateUserRequest(BaseModel):
    """创建用户请求"""
    email: EmailStr = Field(..., description="用户邮箱")
    notes: Optional[str] = Field("", description="备注信息")


class UpdateUserRequest(BaseModel):
    """更新用户请求"""
    email: Optional[EmailStr] = Field(None, description="用户邮箱")
    enabled: Optional[bool] = Field(None, description="是否启用")
    notes: Optional[str] = Field(None, description="备注信息")


# ==================== 响应模型 ====================

class UserResponse(BaseModel):
    """用户信息响应"""
    id: int
    uuid: str
    email: str
    secret_path: str
    level: int
    enabled: bool
    notes: Optional[str]
    created_at: str
    updated_at: str
    vless_link: Optional[str] = Field(None, description="VLESS 连接链接")


class CreateUserResponse(BaseModel):
    """创建用户响应"""
    success: bool
    message: str
    user: Optional[UserResponse]


class UserListResponse(BaseModel):
    """用户列表响应"""
    success: bool
    count: int
    users: List[UserResponse]


class ReloadConfigResponse(BaseModel):
    """配置重载响应"""
    success: bool
    message: str
    user_count: int


class DeviceAccessLog(BaseModel):
    """设备访问记录"""
    id: int
    user_id: int
    user_agent: str
    source_ip: str
    accessed_path: str
    first_seen_at: str
    last_seen_at: str
    access_count: int
    notes: Optional[str]


class DeviceListResponse(BaseModel):
    """设备列表响应"""
    success: bool
    count: int
    devices: List[DeviceAccessLog]


class ErrorResponse(BaseModel):
    """错误响应"""
    success: bool = False
    message: str
    detail: Optional[str] = None
