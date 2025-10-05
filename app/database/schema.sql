-- Avalon Tunnel 数据库架构
-- SQLite 数据库，存储所有持久化配置和用户信息

-- 用户表：存储所有 V2Ray 用户配置
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    uuid TEXT NOT NULL UNIQUE,          -- V2Ray 认证 UUID（固定，不轮换）
    email TEXT NOT NULL UNIQUE,         -- 用户邮箱（唯一标识）
    secret_path TEXT NOT NULL UNIQUE,   -- 用户专属秘密路径（固定，不轮换）
    level INTEGER DEFAULT 0,            -- 权限等级
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    enabled INTEGER DEFAULT 1,          -- 1: 启用, 0: 禁用
    notes TEXT                          -- 用户备注
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_users_uuid ON users(uuid);
CREATE INDEX IF NOT EXISTS idx_users_secret_path ON users(secret_path);
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

-- 插入默认用户 (Morgan)
-- UUID 和 SECRET_PATH 在首次部署时由 Python 程序填充
INSERT OR IGNORE INTO users (uuid, email, secret_path, level, enabled, notes) VALUES
    (
        'a1b2c3d4-e5f6-7890-abcd-ef1234567890',  -- 固定 UUID（方便调试和识别）
        'Morgan@avalon-tunnel.com',               -- 默认用户邮箱
        '',                                       -- SECRET_PATH 初始为空，首次部署时生成
        0,                                         -- 默认权限等级
        1,                                         -- 启用状态
        '系统默认用户 - 数据库初始化时自动创建'    -- 备注说明
    );

-- 设备访问记录表：追踪用户设备访问情况（仅记录，不限制）
CREATE TABLE IF NOT EXISTS device_access_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,               -- 关联用户 ID
    user_agent TEXT,                        -- User-Agent 字符串（推断设备类型）
    source_ip TEXT,                         -- 原始 IP 地址
    accessed_path TEXT,                     -- 访问的秘密路径
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,  -- 首次访问时间
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,   -- 最后访问时间
    access_count INTEGER DEFAULT 1,         -- 访问次数
    notes TEXT,                             -- 备注
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- 设备访问记录索引（用于快速查询某用户的设备）
CREATE UNIQUE INDEX IF NOT EXISTS idx_device_unique ON device_access_logs(user_id, user_agent, source_ip);
CREATE INDEX IF NOT EXISTS idx_device_user_id ON device_access_logs(user_id);
CREATE INDEX IF NOT EXISTS idx_device_last_seen ON device_access_logs(last_seen_at);

-- 审计日志表：记录配置变更历史（API 操作日志）
CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    action TEXT NOT NULL,  -- 操作类型: create_user, delete_user, update_config, restart_v2ray
    target TEXT,           -- 操作对象: user_id, setting_key
    details TEXT,          -- JSON 格式的详细信息
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

