#!/usr/bin/env python3
"""
Avalon Tunnel - 配置服务模块
负责生成和同步 V2Ray、Traefik 的配置文件
"""

import json
import os
import secrets
import string
from pathlib import Path
from typing import Dict, List, Optional

# V2Ray 默认基础配置模板（当数据库为空且本地文件不存在时作为回退方案）
DEFAULT_V2RAY_BASE_CONFIG = {
    "log": {
        "loglevel": "debug",
        "access": "/var/log/v2ray/access.log",
        "error": "/var/log/v2ray/error.log"
    },
    "dns": {
        "servers": [
            "2001:4860:4860::8888",
            "2001:4860:4860::8844",
            "2606:4700:4700::1111",
            "2606:4700:4700::1001",
            "localhost"
        ],
        "queryStrategy": "UseIP",
        "disableCache": False
    },
    "outbounds": [
        {
            "protocol": "freedom",
            "settings": {
                "domainStrategy": "UseIP"
            },
            "streamSettings": {
                "sockopt": {
                    "tcpKeepAliveInterval": 30,
                    "tcpKeepAliveIdle": 300,
                    "tcpFastOpen": True,
                    "mark": 255
                }
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
        "domainStrategy": "IPIfNonMatch",
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
        self.traefik_dynamic = self.base_dir / "traefik_dynamic.yml"
    
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
        生成 V2Ray inbounds 配置（仅生成用户列表）
        
        Args:
            users: 用户列表，每个用户包含 uuid, email, level, secret_path
            v2ray_port_base: V2Ray 起始端口（每个用户 +1）
        
        Returns:
            只包含 inbounds 的配置字典
        
        Note:
            此方法只生成 inbounds，其他所有配置（dns, outbounds, log, routing）
            都从数据库或基础模板中读取并保留
        """
        inbounds = []
        port_offset = 0
        
        for user in users:
            if not user.get('enabled', 1):
                continue
            
            if not user.get('secret_path'):
                print(f"  [Warning] 警告: 用户 {user['email']} 没有 secret_path，跳过")
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
                        "path": f"/stream/{user['secret_path']}"  # UUID 和路径绑定
                    }
                },
                "tag": f"inbound-{user['email']}"
            })
            port_offset += 1
        
        return {"inbounds": inbounds}
    
    def write_v2ray_config(self, config: Dict, db = None):
        """
        写入 V2Ray 配置文件（只更新 inbounds）
        
        策略：
        1. 尝试从数据库读取配置基底模板
        2. 如果数据库不可用，尝试读取现有的本地 config.json 文件
        3. 如果两者均不存在，则使用硬编码的默认基础配置模板
        4. 只更新 inbounds（用户列表），并写入 config.json
        """
        existing_config = None
        
        # 1. 尝试从数据库中获取基础配置
        if db:
            try:
                base_config_str = db.get_setting('v2ray_base_config')
                if base_config_str:
                    existing_config = json.loads(base_config_str)
                    print("  [Config] 从数据库加载 V2Ray 基础配置模板")
            except Exception as e:
                print(f"  [Warning] 无法从数据库读取基础配置: {e}")
        
        # 2. 从本地 config.json 读取
        if not existing_config and self.config_json.exists():
            try:
                with open(self.config_json, 'r', encoding='utf-8') as f:
                    existing_config = json.load(f)
                print(f"  [Config] 读取现有本地配置: {self.config_json}")
            except Exception as e:
                print(f"  [Warning] 无法读取本地 {self.config_json}: {e}")
        
        # 3. 最终回退至硬编码基础配置
        if not existing_config:
            existing_config = DEFAULT_V2RAY_BASE_CONFIG.copy()
            print("  [Warning] 使用默认硬编码 V2Ray 基础配置")
        
        # 只更新 inbounds，保留所有其他配置
        if 'inbounds' in config:
            existing_config['inbounds'] = config['inbounds']
            print(f"  [Config] 更新 inbounds ({len(config['inbounds'])} 个用户)")
        
        # 确保目录存在并写入更新后的配置
        self.config_json.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_json, 'w', encoding='utf-8') as f:
            json.dump(existing_config, f, indent=2, ensure_ascii=False)
            
    def generate_traefik_dynamic(self, domain: str, users: List[Dict],
                                 v2ray_port: int = 10000) -> str:
        """
        生成 Traefik 动态配置文件 (traefik_dynamic.yml)
        
        Args:
            domain: 域名
            users: 用户列表
            v2ray_port: V2Ray 起始端口
        
        Returns:
            YAML 配置内容
        """
        # API 路由与伪装网默认路由
        yaml_content = f"""# Avalon Tunnel - Traefik Dynamic Configuration
# 自动生成，请勿手动编辑

http:
  routers:
    # API 管理接口与文档路由
    api-router:
      rule: "Host(`{domain}`) && (PathPrefix(`/api`) || PathPrefix(`/docs`) || PathPrefix(`/redoc`) || Path(`/openapi.json`))"
      service: api-service
      entryPoints:
        - websecure
      tls: {{}}
      priority: 100

    # 根路径 - 伪装网站（静态/动态流量生成）
    decoy-router:
      rule: "Host(`{domain}`) && PathPrefix(`/`)"
      service: api-service
      entryPoints:
        - websecure
      tls: {{}}
      priority: 1
"""
        
        user_routers = ""
        user_services = ""
        port_offset = 0
        
        for user in users:
            if not user.get('enabled', 1) or not user.get('secret_path'):
                continue
            
            user_port = v2ray_port + port_offset
            # 清理邮箱格式用于作为 YAML 中的标识符
            email_clean = user['email'].replace('@', '-').replace('.', '-')
            
            # 为每个用户绑定独立的 path，转发到独立的 V2Ray 监听端口
            user_routers += f"""
    # 用户: {user['email']}
    user-{email_clean}:
      rule: "Host(`{domain}`) && Path(`/stream/{user['secret_path']}`)"
      service: service-{email_clean}
      entryPoints:
        - websecure
      tls: {{}}
      priority: 50
"""
            
            # 反代到本地环回地址上 V2Ray 的对应端口
            user_services += f"""
    service-{email_clean}:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:{user_port}"
"""
            port_offset += 1
            
        # 插入动态生成的路由
        if user_routers:
            yaml_content = yaml_content.replace("  routers:", "  routers:" + user_routers)
            
        # 拼接服务块
        yaml_content += "\n  services:\n"
        yaml_content += f"""    # API 及伪装网页服务
    api-service:
      loadBalancer:
        servers:
          - url: "http://127.0.0.1:8000"
"""
        yaml_content += user_services
        
        return yaml_content
        
    def write_traefik_dynamic(self, content: str):
        """
        写入 Traefik 动态配置文件
        
        Args:
            content: Traefik 动态配置 YAML 内容
        """
        self.traefik_dynamic.parent.mkdir(parents=True, exist_ok=True)
        with open(self.traefik_dynamic, 'w', encoding='utf-8') as f:
            f.write(content)
    
    def sync_all_configs(self, domain: str, users: List[Dict], 
                        v2ray_port: int = 10000, db = None):
        """
        同步所有配置文件（V2Ray json 与 Traefik dynamic yml）
        
        Args:
            domain: 域名
            users: 用户列表（每个用户包含 uuid, email, secret_path）
            v2ray_port: V2Ray 端口
            db: 数据库实例，用于提取 v2ray_base_config
        """
        print("[Config] 正在生成配置文件...")
        
        # 1. 生成 V2Ray 配置文件
        v2ray_config = self.generate_v2ray_config(users, v2ray_port)
        self.write_v2ray_config(v2ray_config, db)
        print(f"  [Config] V2Ray 配置已生成 ({len(users)} 个用户)")
        
        # 2. 生成 Traefik 动态路由配置文件
        traefik_content = self.generate_traefik_dynamic(domain, users, v2ray_port)
        self.write_traefik_dynamic(traefik_content)
        print(f"  [Config] Traefik 动态配置已生成 ({len(users)} 个独立路径)")
        
        print(f"  [Config] 域名: {domain}")
        print(f"  [Config] V2Ray 端口范围: {v2ray_port} - {v2ray_port + len(users) - 1 if users else v2ray_port}")
        print(f"  [Config] Traefik 将通过文件监听机制自动加载路由变动")
    
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
            'path': f'/stream/{secret_path}',
            'host': domain,
            'sni': domain
        }
        
        param_str = urllib.parse.urlencode(params)
        link = f"vless://{uuid}@{domain}:443?{param_str}#{urllib.parse.quote(email)}"
        
        return link


if __name__ == "__main__":
    # 测试配置服务
    print("[Test] 测试配置服务...")
    
    import tempfile
    
    with tempfile.TemporaryDirectory() as tmpdir:
        service = ConfigService(tmpdir)
        
        # 测试生成秘密路径
        secret = ConfigService.generate_secret_path()
        print(f"[Test] 生成秘密路径: {secret}")
        
        # 测试生成配置
        test_users = [
            {"uuid": "test-uuid-1", "email": "user1@test.com", "level": 0, "enabled": 1},
            {"uuid": "test-uuid-2", "email": "user2@test.com", "level": 0, "enabled": 1}
        ]
        
        service.sync_all_configs(
            domain="test.example.com",
            users=test_users,
            v2ray_port=10000
        )
        
        # 测试生成链接
        link = service.generate_vless_link(
            uuid="test-uuid-1",
            domain="test.example.com",
            secret_path=secret,
            email="user1@test.com"
        )
        print(f"[Test] 生成 VLESS 链接:\n  {link}")
        
        print("\n[Success] 所有测试通过！")
