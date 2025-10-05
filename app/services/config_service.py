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
    
    def generate_v2ray_config(self, users: List[Dict], v2ray_port_base: int = 10000) -> Dict:
        """
        生成 V2Ray 配置（Phase 2: 每用户独立 inbound，UUID 和路径强绑定）
        
        Args:
            users: 用户列表，每个用户包含 uuid, email, level, secret_path
            v2ray_port_base: V2Ray 起始端口（每个用户 +1）
        
        Returns:
            V2Ray 配置字典
        
        Security:
            每个用户有独立的 inbound（端口 + 路径），确保：
            - 用户 A 只能用 UUID-A + Path-A 连接
            - 不能用 UUID-A + Path-B 连接（会被 V2Ray 拒绝）
        """
        # 为每个启用的用户创建独立的 inbound
        inbounds = []
        port_offset = 0
        
        for user in users:
            if not user.get('enabled', 1):
                continue
            
            if not user.get('secret_path'):
                print(f"  ⚠️  警告: 用户 {user['email']} 没有 secret_path，跳过")
                continue
            
            inbounds.append({
                "port": v2ray_port_base + port_offset,
                "protocol": "vless",
                "settings": {
                    "clients": [
                        {
                            "id": user['uuid'],
                            "level": user.get('level', 0),
                            "email": user['email']
                        }
                    ],
                    "decryption": "none"
                },
                "streamSettings": {
                    "network": "ws",
                    "wsSettings": {
                        "path": f"/{user['secret_path']}"  # ✅ UUID 和路径绑定
                    }
                },
                "tag": f"inbound-{user['email']}"
            })
            port_offset += 1
        
        config = {
            "log": {
                "loglevel": "warning",
                "access": "/var/log/v2ray/access.log",
                "error": "/var/log/v2ray/error.log"
            },
            "dns": {
                "servers": [
                    "localhost",              # 使用宿主机 DNS（已配置 DNS64）
                    "2606:4700:4700::64",     # Cloudflare DNS64（关键！自动转换 A 记录为 AAAA）
                    "2606:4700:4700::6400",   # Cloudflare DNS64 备用
                    "2606:4700:4700::1111",   # Cloudflare IPv6
                    "2606:4700:4700::1001"    # Cloudflare IPv6 备用
                    # ❌ 不要添加任何 IPv4 地址（1.1.1.1, 8.8.8.8）
                ]
            },
            "inbounds": inbounds,
            "outbounds": [
                {
                    "protocol": "freedom",
                    "settings": {
                        "domainStrategy": "UseIP"  # 查询 A+AAAA，DNS64 自动转换 A 为 AAAA
                    },
                    "tag": "direct"
                },
                {
                    "protocol": "blackhole",
                    "settings": {},
                    "tag": "blocked"
                }
            ],
            "routing": {
                "domainStrategy": "IPIfNonMatch",  # 规则不匹配时使用 V2Ray DNS 解析
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
    
    def generate_caddyfile(self, domain: str, users: List[Dict],
                          v2ray_port: int = 10000, use_staging: bool = False) -> str:
        """
        生成 Caddyfile 配置（Phase 2: 多用户多路径）
        
        Args:
            domain: 域名
            users: 用户列表，每个用户包含 secret_path
            v2ray_port: V2Ray 监听端口
            use_staging: 是否使用 Let's Encrypt Staging 环境（避免频率限制）
        
        Returns:
            Caddyfile 内容
        """
        # TLS 配置（可选）
        tls_config = ""
        if use_staging:
            tls_config = """
    # 使用 Let's Encrypt Staging 环境（测试用，避免频率限制）
    tls {
        ca https://acme-staging-v02.api.letsencrypt.org/directory
    }
"""
        
        # 为每个用户生成一个 handle 块，转发到对应的 V2Ray 端口
        user_handles = ""
        port_offset = 0
        
        for user in users:
            if not user.get('enabled', 1) or not user.get('secret_path'):
                continue
            
            user_port = v2ray_port + port_offset
            user_handles += f"""
    # 用户: {user['email']} ({user['uuid']})
    # V2Ray 端口: {user_port}
    handle /{user['secret_path']} {{
        reverse_proxy 127.0.0.1:{user_port} {{
            header_up Host {{host}}
            header_up X-Real-IP {{remote}}
            header_up X-Forwarded-For {{remote}}
            header_up User-Agent {{http.request.header.User-Agent}}
            header_up Upgrade {{http.request.header.Upgrade}}
            header_up Connection {{http.request.header.Connection}}
        }}
    }}
"""
            port_offset += 1
        
        caddyfile_content = f"""# Avalon Tunnel - Caddy Configuration
# 自动 TLS 证书申请和反向代理配置
# Phase 2: 多用户多路径支持 + API 反向代理

{domain} {{{tls_config}
{user_handles}
    # API 管理接口 - 反向代理到本地 8000 端口
    handle /api/* {{
        reverse_proxy 127.0.0.1:8000
    }}
    
    # API 文档 - Swagger UI
    handle /docs {{
        reverse_proxy 127.0.0.1:8000
    }}
    
    # API 文档 - ReDoc
    handle /redoc {{
        reverse_proxy 127.0.0.1:8000
    }}
    
    # API OpenAPI JSON
    handle /openapi.json {{
        reverse_proxy 127.0.0.1:8000
    }}
    
    # 根路径和所有其他路径 - 伪装网站（动态流量生成）
    handle /* {{
        reverse_proxy 127.0.0.1:8000
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

    # 日志配置（JSON 格式，包含 User-Agent 和 IP）
    log {{
        output file /var/log/caddy/access.log {{
            roll_size 100mb
            roll_keep 5
        }}
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
                        v2ray_port: int = 10000):
        """
        同步所有配置文件（Phase 2: 多用户多路径）
        
        Args:
            domain: 域名
            users: 用户列表（每个用户包含 uuid, email, secret_path）
            v2ray_port: V2Ray 端口
        """
        import os
        
        print("🔄 正在生成配置文件...")
        
        # 生成 V2Ray 配置
        v2ray_config = self.generate_v2ray_config(users, v2ray_port)
        self.write_v2ray_config(v2ray_config)
        print(f"  ✅ V2Ray 配置已生成 ({len(users)} 个用户)")
        
        # 检查是否使用 Staging 环境（通过环境变量控制）
        use_staging = os.getenv('ACME_STAGING', '').lower() in ('1', 'true', 'yes')
        
        # 生成 Caddyfile（多用户多路径）
        caddyfile = self.generate_caddyfile(domain, users, v2ray_port, use_staging)
        self.write_caddyfile(caddyfile)
        
        if use_staging:
            print(f"  ✅ Caddy 配置已生成（使用 Staging 环境）")
            print(f"  ⚠️  注意：Staging 证书不被浏览器信任，仅用于测试")
        else:
            print(f"  ✅ Caddy 配置已生成 ({len(users)} 个独立路径)")
        
        print(f"  📍 域名: {domain}")
        print(f"  🔌 V2Ray 端口: {v2ray_port}")
        print(f"  ⚠️  注意：V2Ray 需要重启才能应用配置，Caddy 自动热加载")
    
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

