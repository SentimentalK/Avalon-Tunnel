#!/usr/bin/env python3
"""
Avalon Tunnel - API 路由
定义所有 REST API 端点
"""

import os
from fastapi import APIRouter, HTTPException, status
from typing import List

from .models import (
    CreateUserRequest, UpdateUserRequest,
    UserResponse, CreateUserResponse, UserListResponse,
    ReloadConfigResponse, DeviceListResponse, ErrorResponse
)
from ..database import Database
from ..services import ConfigService
from ..services.user_service import UserService


# 创建路由器
router = APIRouter(prefix="/api", tags=["api"])

# 初始化服务（将在 app 启动时注入）
db: Database = None
user_service: UserService = None
domain: str = None


def init_services(database: Database, config_service: ConfigService, app_domain: str):
    """
    初始化服务实例
    
    Args:
        database: 数据库实例
        config_service: 配置服务实例
        app_domain: 域名
    """
    global db, user_service, domain
    db = database
    user_service = UserService(database, config_service)
    domain = app_domain


# ==================== 用户管理 API ====================

@router.post("/users", response_model=CreateUserResponse, status_code=status.HTTP_201_CREATED)
async def create_user(request: CreateUserRequest):
    """
    创建新用户
    
    - 自动生成 UUID 和 SECRET_PATH
    - 返回用户信息和 VLESS 连接链接
    """
    try:
        user = user_service.create_user(
            email=request.email,
            notes=request.notes or ""
        )
        
        # 生成 VLESS 链接
        vless_link = user_service.get_user_vless_link(user['uuid'], domain)
        
        user_response = UserResponse(
            **user,
            vless_link=vless_link
        )
        
        return CreateUserResponse(
            success=True,
            message=f"用户 {user['email']} 创建成功",
            user=user_response
        )
    
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"创建用户失败: {str(e)}"
        )


@router.get("/users", response_model=UserListResponse)
async def list_users(enabled_only: bool = False):
    """
    获取所有用户列表
    
    - enabled_only: 是否只返回启用的用户
    """
    try:
        users = user_service.get_all_users(enabled_only=enabled_only)
        
        user_responses = []
        for user in users:
            vless_link = user_service.get_user_vless_link(user['uuid'], domain)
            user_responses.append(UserResponse(
                **user,
                vless_link=vless_link
            ))
        
        return UserListResponse(
            success=True,
            count=len(user_responses),
            users=user_responses
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户列表失败: {str(e)}"
        )


@router.get("/users/{user_uuid}", response_model=UserResponse)
async def get_user(user_uuid: str):
    """
    获取指定用户详情
    """
    user = user_service.get_user(user_uuid)
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 {user_uuid} 不存在"
        )
    
    vless_link = user_service.get_user_vless_link(user['uuid'], domain)
    
    return UserResponse(
        **user,
        vless_link=vless_link
    )


@router.put("/users/{user_uuid}", response_model=UserResponse)
async def update_user(user_uuid: str, request: UpdateUserRequest):
    """
    更新用户信息
    
    - 可更新：email, enabled, notes
    - 不可更新：uuid, secret_path
    """
    # 检查用户是否存在
    user = user_service.get_user(user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 {user_uuid} 不存在"
        )
    
    # 构建更新字段
    update_fields = {}
    if request.email is not None:
        update_fields['email'] = request.email
    if request.enabled is not None:
        update_fields['enabled'] = 1 if request.enabled else 0
    if request.notes is not None:
        update_fields['notes'] = request.notes
    
    if not update_fields:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="没有提供要更新的字段"
        )
    
    # 更新用户
    success = user_service.update_user(user_uuid, **update_fields)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="更新用户失败"
        )
    
    # 返回更新后的用户信息
    updated_user = user_service.get_user(user_uuid)
    vless_link = user_service.get_user_vless_link(user_uuid, domain)
    
    return UserResponse(
        **updated_user,
        vless_link=vless_link
    )


@router.delete("/users/{user_uuid}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_uuid: str):
    """
    删除用户
    """
    user = user_service.get_user(user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 {user_uuid} 不存在"
        )
    
    success = user_service.delete_user(user_uuid)
    
    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="删除用户失败"
        )
    
    return None


# ==================== 配置管理 API ====================

@router.post("/config/reload", response_model=ReloadConfigResponse)
async def reload_config():
    """
    重新生成配置文件并重启 V2Ray
    
    - 从数据库读取所有用户
    - 生成新的 config.json 和 Caddyfile
    - Caddy 自动热加载
    - 重启 V2Ray 容器
    """
    try:
        result = user_service.reload_configs(domain)
        
        if not result['success']:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=result['message']
            )
        
        return ReloadConfigResponse(**result)
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"配置重载失败: {str(e)}"
        )


# ==================== 设备管理 API ====================

@router.get("/devices", response_model=DeviceListResponse)
async def list_all_devices(limit: int = 100):
    """
    获取所有设备访问记录
    
    - limit: 返回的最大记录数
    """
    try:
        devices = db.get_all_device_access(limit=limit)
        
        return DeviceListResponse(
            success=True,
            count=len(devices),
            devices=devices
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取设备列表失败: {str(e)}"
        )


@router.get("/users/{user_uuid}/devices", response_model=DeviceListResponse)
async def list_user_devices(user_uuid: str):
    """
    获取指定用户的设备访问记录
    """
    user = user_service.get_user(user_uuid)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"用户 {user_uuid} 不存在"
        )
    
    try:
        devices = user_service.get_user_devices(user['id'])
        
        return DeviceListResponse(
            success=True,
            count=len(devices),
            devices=devices
        )
    
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"获取用户设备失败: {str(e)}"
        )


# ==================== 健康检查 API ====================

@router.get("/health")
async def health_check():
    """
    健康检查端点
    """
    return {
        "status": "healthy",
        "service": "Avalon Tunnel API",
        "version": "2.0.0"
    }
