#!/usr/bin/env python3
"""
Avalon Tunnel - 用户管理业务逻辑
封装用户 CRUD 操作和配置重载逻辑
"""

import subprocess
from typing import List, Dict, Optional
from pathlib import Path

from ..database import Database
from .config_service import ConfigService


class UserService:
    """用户管理服务"""
    
    def __init__(self, db: Database, config_service: ConfigService):
        """
        初始化用户服务
        
        Args:
            db: 数据库实例
            config_service: 配置服务实例
        """
        self.db = db
        self.config_service = config_service
    
    def create_user(self, email: str, notes: str = "") -> Dict:
        """
        创建新用户
        
        Args:
            email: 用户邮箱
            notes: 备注信息
        
        Returns:
            创建的用户信息（包含 UUID 和 SECRET_PATH）
        
        Raises:
            ValueError: 如果用户已存在或创建失败
        """
        # 1. 生成秘密路径
        secret_path = ConfigService.generate_secret_path(32)
        
        # 2. 创建用户记录
        user = self.db.create_user(
            email=email,
            secret_path=secret_path,
            notes=notes
        )
        
        return user
    
    def get_all_users(self, enabled_only: bool = False) -> List[Dict]:
        """
        获取所有用户
        
        Args:
            enabled_only: 是否只返回启用的用户
        
        Returns:
            用户列表
        """
        return self.db.get_all_users(enabled_only=enabled_only)
    
    def get_user(self, user_uuid: str) -> Optional[Dict]:
        """
        根据 UUID 获取用户
        
        Args:
            user_uuid: 用户 UUID
        
        Returns:
            用户信息，如果不存在则返回 None
        """
        return self.db.get_user_by_uuid(user_uuid)
    
    def update_user(self, user_uuid: str, **kwargs) -> bool:
        """
        更新用户信息
        
        Args:
            user_uuid: 用户 UUID
            **kwargs: 要更新的字段（email, level, enabled, notes）
        
        Returns:
            是否更新成功
        """
        return self.db.update_user(user_uuid, **kwargs)
    
    def delete_user(self, user_uuid: str) -> bool:
        """
        删除用户
        
        Args:
            user_uuid: 用户 UUID
        
        Returns:
            是否删除成功
        """
        return self.db.delete_user(user_uuid)
    
    def reload_configs(self, domain: str) -> Dict:
        """
        重新生成配置文件并重启 V2Ray
        
        Args:
            domain: 域名
        
        Returns:
            操作结果
        """
        try:
            # 1. 获取所有启用的用户
            users = self.db.get_all_users(enabled_only=True)
            v2ray_port = int(self.db.get_setting('v2ray_port') or 10000)
            
            # 2. 生成配置文件
            self.config_service.sync_all_configs(
                domain=domain,
                users=users,
                v2ray_port=v2ray_port
            )
            
            # 3. 重启 V2Ray 容器（Caddy 自动热加载）
            # 使用外部脚本，避免在容器内安装 Docker CLI
            restart_script = Path(__file__).parent.parent.parent / 'scripts' / 'restart-v2ray.sh'
            result = subprocess.run(
                ['bash', str(restart_script)],
                capture_output=True,
                text=True,
                timeout=30
            )
            
            if result.returncode == 0:
                return {
                    'success': True,
                    'message': f'配置已更新，V2Ray 已重启（{len(users)} 个用户）',
                    'user_count': len(users)
                }
            else:
                return {
                    'success': False,
                    'message': f'V2Ray 重启失败: {result.stderr}',
                    'user_count': len(users)
                }
        
        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'message': 'V2Ray 重启超时（30秒）',
                'user_count': len(users) if 'users' in locals() else 0
            }
        except Exception as e:
            return {
                'success': False,
                'message': f'配置重载失败: {str(e)}',
                'user_count': 0
            }
    
    def get_user_vless_link(self, user_uuid: str, domain: str) -> Optional[str]:
        """
        生成用户的 VLESS 连接链接
        
        Args:
            user_uuid: 用户 UUID
            domain: 域名
        
        Returns:
            VLESS 链接，如果用户不存在则返回 None
        """
        user = self.db.get_user_by_uuid(user_uuid)
        if not user or not user.get('secret_path'):
            return None
        
        return self.config_service.generate_vless_link(
            uuid=user['uuid'],
            domain=domain,
            secret_path=user['secret_path'],
            email=user['email']
        )
    
    def get_user_devices(self, user_id: int) -> List[Dict]:
        """
        获取用户的设备访问记录
        
        Args:
            user_id: 用户 ID
        
        Returns:
            设备访问记录列表
        """
        return self.db.get_user_devices(user_id)
