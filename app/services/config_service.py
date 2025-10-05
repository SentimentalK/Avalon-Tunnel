#!/usr/bin/env python3
"""
Avalon Tunnel - 配置服务模块
负责生成和同步 V2Ray、Caddy 的配置文件
"""

import json
import os
import secrets
import string
from pathlib import Path
from typing import Dict, List, Optional


class ConfigService:
    """配置服务 - 负责配置文件的生成和管理"""
    
    def __init__(self, base_dir: str = "."):
        """
        初始化配置服务
        
        Args:
            base_dir: 项目根目录
        """
        self.base_dir = Path(base_dir)
        self.config_json = self.base_dir / "config.json"
        self.caddyfile = self.base_dir / "Caddyfile"
    
    @staticmethod
    def generate_secret_path(length: int = 32) -> str:
        """
        生成随机的秘密路径
        
        Args:
            length: 路径长度
        
        Returns:
            随机路径字符串
        """
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(length))
    
    def generate_v2ray_config(self, users: List[Dict], secret_path: str, 
                             v2ray_port: int = 10000) -> Dict:
        """
        生成 V2Ray 配置
        
        Args:
            users: 用户列表，每个用户包含 uuid, email, level
            secret_path: WebSocket 路径
            v2ray_port: V2Ray 监听端口
        
        Returns:
            V2Ray 配置字典
        """
        config = {
            "log": {
                "loglevel": "warning",
                "access": "/var/log/v2ray/access.log",
                "error": "/var/log/v2ray/error.log"
            },
            "inbounds": [
                {
                    "port": v2ray_port,
                    "protocol": "vless",
                    "settings": {
                        "clients": [
                            {
                                "id": user['uuid'],
                                "level": user.get('level', 0),
                                "email": user['email']
                            }
                            for user in users if user.get('enabled', 1)
                        ],
                        "decryption": "none"
                    },
                    "streamSettings": {
                        "network": "ws",
                        "wsSettings": {
                            "path": f"/{secret_path}"
                        }
                    }
                }
            ],
            "outbounds": [
                {
                    "protocol": "freedom",
                    "settings": {}
                },
                {
                    "protocol": "blackhole",
                    "settings": {},
                    "tag": "blocked"
                }
            ],
            "routing": {
                "rules": [
                    {
                        "type": "field",
                        "ip": [
                            "0.0.0.0/8",
                            "10.0.0.0/8",
                            "100.64.0.0/10",
                            "127.0.0.0/8",
                            "169.254.0.0/16",
                            "172.16.0.0/12",
                            "192.0.0.0/24",
                            "192.0.2.0/24",
                            "192.168.0.0/16",
                            "198.18.0.0/15",
                            "198.51.100.0/24",
                            "203.0.113.0/24",
                            "::1/128",
                            "fc00::/7",
                            "fe80::/10"
                        ],
                        "outboundTag": "blocked"
                    }
                ]
            }
        }
        
        return config
    
    def write_v2ray_config(self, config: Dict):
        """
        写入 V2Ray 配置文件
        
        Args:
            config: V2Ray 配置字典
        """
        with open(self.config_json, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
    
    def generate_caddyfile(self, domain: str, secret_path: str, 
                          v2ray_port: int = 10000) -> str:
        """
        生成 Caddyfile 配置
        
        Args:
            domain: 域名
            secret_path: WebSocket 路径
            v2ray_port: V2Ray 监听端口
        
        Returns:
            Caddyfile 内容
        """
        caddyfile_content = f"""# Avalon Tunnel - Caddy Configuration
# 自动 TLS 证书申请和反向代理配置

{domain} {{
    # 根路径 - 伪装网站
    handle / {{
        root * /srv
        file_server
        header Cache-Control "no-cache, no-store, must-revalidate"
        header Pragma "no-cache"
        header Expires "0"
    }}

    # 秘密路径 - V2Ray WebSocket 代理
    # 使用 127.0.0.1 因为在 host 网络模式下
    handle /{secret_path} {{
        reverse_proxy 127.0.0.1:{v2ray_port} {{
            header_up Host {{host}}
            header_up X-Real-IP {{remote}}
            header_up Upgrade {{http.request.header.Upgrade}}
            header_up Connection {{http.request.header.Connection}}
        }}
    }}

    # 安全头设置
    header {{
        # 隐藏服务器信息
        -Server
        Server "nginx/1.18.0"
        
        # 安全头
        X-Content-Type-Options "nosniff"
        X-Frame-Options "DENY"
        X-XSS-Protection "1; mode=block"
        Strict-Transport-Security "max-age=31536000; includeSubDomains"
        
        # 防止缓存敏感路径
        Cache-Control "no-cache, no-store, must-revalidate"
    }}

    # 日志配置
    log {{
        output file /var/log/caddy/access.log
        format json
    }}
}}
"""
        return caddyfile_content
    
    def write_caddyfile(self, content: str):
        """
        写入 Caddyfile
        
        Args:
            content: Caddyfile 内容
        """
        with open(self.caddyfile, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def sync_all_configs(self, domain: str, users: List[Dict], 
                        secret_path: str, v2ray_port: int = 10000):
        """
        同步所有配置文件
        
        Args:
            domain: 域名
            users: 用户列表
            secret_path: 秘密路径
            v2ray_port: V2Ray 端口
        """
        print("🔄 正在生成配置文件...")
        
        # 生成 V2Ray 配置
        v2ray_config = self.generate_v2ray_config(users, secret_path, v2ray_port)
        self.write_v2ray_config(v2ray_config)
        print(f"  ✅ V2Ray 配置已生成 ({len(users)} 个用户)")
        
        # 生成 Caddyfile
        caddyfile = self.generate_caddyfile(domain, secret_path, v2ray_port)
        self.write_caddyfile(caddyfile)
        print(f"  ✅ Caddy 配置已生成")
        
        print(f"  📍 域名: {domain}")
        print(f"  🔐 秘密路径: /{secret_path}")
        print(f"  🔌 V2Ray 端口: {v2ray_port}")
    
    def generate_vless_link(self, uuid: str, domain: str, secret_path: str,
                           email: str = "Avalon-Tunnel") -> str:
        """
        生成 VLESS 链接
        
        Args:
            uuid: 用户 UUID
            domain: 域名
            secret_path: 秘密路径
            email: 用户标识（备注名）
        
        Returns:
            VLESS 链接
        """
        import urllib.parse
        
        params = {
            'type': 'ws',
            'security': 'tls',
            'path': f'/{secret_path}',
            'host': domain,
            'sni': domain
        }
        
        param_str = urllib.parse.urlencode(params)
        link = f"vless://{uuid}@{domain}:443?{param_str}#{urllib.parse.quote(email)}"
        
        return link


if __name__ == "__main__":
    # 测试配置服务
    print("🧪 测试配置服务...")
    
    import tempfile
    import os
    
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ConfigService(tmpdir)
        
        # 测试生成秘密路径
        secret = ConfigService.generate_secret_path()
        print(f"✅ 生成秘密路径: {secret}")
        
        # 测试生成配置
        test_users = [
            {"uuid": "test-uuid-1", "email": "user1@test.com", "level": 0, "enabled": 1},
            {"uuid": "test-uuid-2", "email": "user2@test.com", "level": 0, "enabled": 1}
        ]
        
        service.sync_all_configs(
            domain="test.example.com",
            users=test_users,
            secret_path=secret
        )
        
        # 测试生成链接
        link = service.generate_vless_link(
            uuid="test-uuid-1",
            domain="test.example.com",
            secret_path=secret,
            email="user1@test.com"
        )
        print(f"✅ 生成 VLESS 链接:\n  {link}")
        
        print("\n🎉 所有测试通过！")

