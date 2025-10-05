-- Avalon Tunnel 数据库架构
-- SQLite 数据库，存储所有持久化配置和用户信息

-- 用户表：存储所有 V2Ray 用户配置
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,
    email TEXT NOT NULL UNIQUE,
    level INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    enabled INTEGER DEFAULT 1,  -- 1: 启用, 0: 禁用
    notes TEXT  -- 用户备注
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_users_uuid ON users(uuid);
CREATE INDEX IF NOT EXISTS idx_users_enabled ON users(enabled);

-- 系统设置表：存储全局配置
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    description TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 插入默认系统设置
INSERT OR IGNORE INTO settings (key, value, description) VALUES
    ('secret_path', '', 'V2Ray WebSocket 秘密路径 (自动生成)'),
    ('v2ray_port', '10000', 'V2Ray 监听端口'),
    ('initialized', '0', '系统是否已初始化 (0: 否, 1: 是)');

-- 审计日志表：记录配置变更历史 (为未来 API 准备)
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,  -- 操作类型: create_user, delete_user, update_config
    target TEXT,  -- 操作对象: user_id, setting_key
    details TEXT,  -- JSON 格式的详细信息
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建触发器：自动更新 updated_at 字段
CREATE TRIGGER IF NOT EXISTS update_users_timestamp 
AFTER UPDATE ON users
BEGIN
    UPDATE users SET updated_at = CURRENT_TIMESTAMP WHERE id = NEW.id;
END;

CREATE TRIGGER IF NOT EXISTS update_settings_timestamp 
AFTER UPDATE ON settings
BEGIN
    UPDATE settings SET updated_at = CURRENT_TIMESTAMP WHERE key = NEW.key;
END;

