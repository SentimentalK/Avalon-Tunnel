#!/usr/bin/env python3
"""
Avalon Tunnel - 数据库模块
负责所有数据库操作，实现数据访问层 (DAL)
"""

import sqlite3
import uuid
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from datetime import datetime


class Database:
    """数据库管理类 - 单一数据源"""
    
    def __init__(self, db_path: str = "data/avalon.db"):
        """
        初始化数据库连接
        
        Args:
            db_path: 数据库文件路径
        """
        self.db_path = Path(db_path)
        self.schema_path = Path(__file__).parent / "schema.sql"
        
        # 确保数据目录存在
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # 检查是否是首次初始化
        self.is_first_init = not self.db_path.exists()
        
        # 初始化数据库
        self._init_database()
    
    def _get_connection(self) -> sqlite3.Connection:
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 使用字典式访问
        return conn
    
    def _init_database(self):
        """初始化数据库（创建表结构）"""
        if not self.schema_path.exists():
            raise FileNotFoundError(f"数据库架构文件不存在: {self.schema_path}")
        
        # 读取 schema.sql
        with open(self.schema_path, 'r', encoding='utf-8') as f:
            schema_sql = f.read()
        
        # 执行建表语句
        conn = self._get_connection()
        try:
            conn.executescript(schema_sql)
            conn.commit()
        finally:
            conn.close()
    
    def is_initialized(self) -> bool:
        """检查系统是否已初始化"""
        setting = self.get_setting('initialized')
        return setting == '1' if setting else False
    
    def mark_as_initialized(self):
        """标记系统为已初始化"""
        self.set_setting('initialized', '1')
    
    # ==================== 用户管理 ====================
    
    def create_user(self, email: str, user_uuid: Optional[str] = None, 
                   level: int = 0, notes: str = "") -> Dict:
        """
        创建新用户
        
        Args:
            email: 用户邮箱
            user_uuid: 用户 UUID（如果不提供则自动生成）
            level: 用户等级
            notes: 备注信息
        
        Returns:
            创建的用户信息
        """
        if not user_uuid:
            user_uuid = str(uuid.uuid4())
        
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "INSERT INTO users (uuid, email, level, notes) VALUES (?, ?, ?, ?)",
                (user_uuid, email, level, notes)
            )
            conn.commit()
            
            # 记录审计日志
            self._log_audit("create_user", f"user:{cursor.lastrowid}", 
                          f"Created user {email} with UUID {user_uuid}")
            
            return self.get_user_by_uuid(user_uuid)
        except sqlite3.IntegrityError as e:
            raise ValueError(f"用户创建失败（UUID 或邮箱可能已存在）: {e}")
        finally:
            conn.close()
    
    def get_user_by_uuid(self, user_uuid: str) -> Optional[Dict]:
        """根据 UUID 获取用户"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM users WHERE uuid = ?", (user_uuid,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def get_user_by_email(self, email: str) -> Optional[Dict]:
        """根据邮箱获取用户"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM users WHERE email = ?", (email,)
            )
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()
    
    def get_all_users(self, enabled_only: bool = True) -> List[Dict]:
        """
        获取所有用户
        
        Args:
            enabled_only: 是否只返回启用的用户
        """
        conn = self._get_connection()
        try:
            if enabled_only:
                cursor = conn.execute(
                    "SELECT * FROM users WHERE enabled = 1 ORDER BY created_at"
                )
            else:
                cursor = conn.execute(
                    "SELECT * FROM users ORDER BY created_at"
                )
            
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
    
    def update_user(self, user_uuid: str, **kwargs) -> bool:
        """
        更新用户信息
        
        Args:
            user_uuid: 用户 UUID
            **kwargs: 要更新的字段（email, level, enabled, notes）
        """
        allowed_fields = ['email', 'level', 'enabled', 'notes']
        updates = {k: v for k, v in kwargs.items() if k in allowed_fields}
        
        if not updates:
            return False
        
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [user_uuid]
        
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                f"UPDATE users SET {set_clause} WHERE uuid = ?",
                values
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                self._log_audit("update_user", f"user:{user_uuid}", 
                              f"Updated: {updates}")
                return True
            return False
        finally:
            conn.close()
    
    def delete_user(self, user_uuid: str) -> bool:
        """删除用户"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "DELETE FROM users WHERE uuid = ?", (user_uuid,)
            )
            conn.commit()
            
            if cursor.rowcount > 0:
                self._log_audit("delete_user", f"user:{user_uuid}", 
                              f"Deleted user {user_uuid}")
                return True
            return False
        finally:
            conn.close()
    
    def disable_user(self, user_uuid: str) -> bool:
        """禁用用户（软删除）"""
        return self.update_user(user_uuid, enabled=0)
    
    def enable_user(self, user_uuid: str) -> bool:
        """启用用户"""
        return self.update_user(user_uuid, enabled=1)
    
    # ==================== 系统设置 ====================
    
    def get_setting(self, key: str) -> Optional[str]:
        """获取系统设置"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT value FROM settings WHERE key = ?", (key,)
            )
            row = cursor.fetchone()
            return row['value'] if row else None
        finally:
            conn.close()
    
    def set_setting(self, key: str, value: str, description: str = ""):
        """设置系统配置"""
        conn = self._get_connection()
        try:
            conn.execute(
                """
                INSERT INTO settings (key, value, description) 
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = ?, updated_at = CURRENT_TIMESTAMP
                """,
                (key, value, description, value)
            )
            conn.commit()
            
            self._log_audit("update_setting", f"setting:{key}", 
                          f"Set {key} = {value}")
        finally:
            conn.close()
    
    def get_all_settings(self) -> Dict[str, str]:
        """获取所有设置"""
        conn = self._get_connection()
        try:
            cursor = conn.execute("SELECT key, value FROM settings")
            return {row['key']: row['value'] for row in cursor.fetchall()}
        finally:
            conn.close()
    
    # ==================== 审计日志 ====================
    
    def _log_audit(self, action: str, target: str, details: str):
        """记录审计日志（内部方法）"""
        conn = self._get_connection()
        try:
            conn.execute(
                "INSERT INTO audit_logs (action, target, details) VALUES (?, ?, ?)",
                (action, target, details)
            )
            conn.commit()
        except Exception:
            pass  # 审计日志失败不应该影响主要操作
        finally:
            conn.close()
    
    def get_audit_logs(self, limit: int = 100) -> List[Dict]:
        """获取审计日志"""
        conn = self._get_connection()
        try:
            cursor = conn.execute(
                "SELECT * FROM audit_logs ORDER BY created_at DESC LIMIT ?",
                (limit,)
            )
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


if __name__ == "__main__":
    # 测试数据库功能
    print("🧪 测试数据库模块...")
    
    # 使用临时数据库测试
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        test_db_path = os.path.join(tmpdir, "test.db")
        db = Database(test_db_path)
        
        print("✅ 数据库初始化成功")
        
        # 测试创建用户
        user = db.create_user(
            email="test@avalon.com",
            notes="测试用户"
        )
        print(f"✅ 创建用户: {user['email']} (UUID: {user['uuid']})")
        
        # 测试查询用户
        users = db.get_all_users()
        print(f"✅ 查询到 {len(users)} 个用户")
        
        # 测试设置
        db.set_setting("secret_path", "test-secret-path")
        secret_path = db.get_setting("secret_path")
        print(f"✅ 设置秘密路径: {secret_path}")
        
        # 测试审计日志
        logs = db.get_audit_logs()
        print(f"✅ 审计日志记录: {len(logs)} 条")
        
        print("\n🎉 所有测试通过！")

