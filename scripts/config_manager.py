#!/usr/bin/env python3
"""
Avalon Tunnel 配置管理器
自动处理环境变量、配置生成、链接生成等所有配置相关任务
"""

import os
import json
import sys
import base64
from pathlib import Path
from typing import Dict, List, Optional
import urllib.parse


class ConfigManager:
    """配置管理器"""
    
    def __init__(self, base_dir: str = "."):
        self.base_dir = Path(base_dir)
        self.env_file = self.base_dir / ".env"
        self.config_file = self.base_dir / "config.json"
        self.caddyfile = self.base_dir / "Caddyfile"
        
    def load_env(self) -> Dict[str, str]:
        """加载环境变量"""
        env_vars = {}
        
        # 从 .env 文件加载
        if self.env_file.exists():
            with open(self.env_file, 'r') as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith('#'):
                        if '=' in line:
                            key, value = line.split('=', 1)
                            env_vars[key.strip()] = value.strip()
        
        # 从系统环境变量加载（优先级更高）
        for key in ['DOMAIN', 'SECRET_PATH']:
            if key in os.environ:
                env_vars[key] = os.environ[key]
        
        # 设置默认值
        env_vars.setdefault('DOMAIN', 'your-domain.com')
        env_vars.setdefault('SECRET_PATH', 'avalon-secret-path')
        
        return env_vars
    
    def load_v2ray_config(self) -> Dict:
        """加载 V2Ray 配置"""
        if not self.config_file.exists():
            raise FileNotFoundError(f"V2Ray 配置文件不存在: {self.config_file}")
        
        with open(self.config_file, 'r') as f:
            return json.load(f)
    
    def get_users(self) -> List[Dict[str, str]]:
        """获取所有用户配置"""
        config = self.load_v2ray_config()
        users = []
        
        for inbound in config.get('inbounds', []):
            protocol = inbound.get('protocol')
            if protocol in ['vless', 'vmess']:
                for client in inbound.get('settings', {}).get('clients', []):
                    users.append({
                        'uuid': client.get('id'),
                        'email': client.get('email', 'user'),
                        'level': client.get('level', 0),
                        'protocol': protocol
                    })
        
        return users
    
    def generate_vless_link(self, uuid: str, domain: str, secret_path: str, 
                           alias: str = "Avalon-Tunnel") -> str:
        """生成 VLESS 链接"""
        # vless://UUID@域名:端口?参数#备注
        params = {
            'type': 'ws',
            'security': 'tls',
            'path': f'/{secret_path}',
            'host': domain,
            'sni': domain
        }
        
        param_str = urllib.parse.urlencode(params)
        link = f"vless://{uuid}@{domain}:443?{param_str}#{urllib.parse.quote(alias)}"
        
        return link
    
    def generate_all_links(self) -> List[Dict[str, str]]:
        """生成所有用户的 VLESS 链接"""
        env = self.load_env()
        domain = env['DOMAIN']
        secret_path = env['SECRET_PATH']
        
        users = self.get_users()
        links = []
        
        for user in users:
            link = self.generate_vless_link(
                uuid=user['uuid'],
                domain=domain,
                secret_path=secret_path,
                alias=user['email']
            )
            links.append({
                'email': user['email'],
                'uuid': user['uuid'],
                'link': link
            })
        
        return links
    
    def update_v2ray_config(self, secret_path: str):
        """更新 V2Ray 配置中的路径"""
        config = self.load_v2ray_config()
        updated = False
        
        for inbound in config.get('inbounds', []):
            if 'streamSettings' in inbound:
                ws_settings = inbound['streamSettings'].get('wsSettings', {})
                current_path = ws_settings.get('path', '')
                new_path = f'/{secret_path}'
                
                if current_path != new_path:
                    ws_settings['path'] = new_path
                    inbound['streamSettings']['wsSettings'] = ws_settings
                    updated = True
        
        if updated:
            with open(self.config_file, 'w') as f:
                json.dump(config, f, indent=2)
            print(f"✅ 已更新 V2Ray WebSocket 路径: /{secret_path}")
        else:
            print(f"✅ V2Ray 路径已是最新: /{secret_path}")
    
    def sync_config(self):
        """同步环境变量到配置文件"""
        env = self.load_env()
        secret_path = env['SECRET_PATH']
        
        print(f"🔄 同步配置...")
        print(f"   域名: {env['DOMAIN']}")
        print(f"   路径: /{secret_path}")
        
        # 更新 V2Ray 配置
        self.update_v2ray_config(secret_path)
        
        print("✅ 配置同步完成")
    
    def validate_config(self) -> bool:
        """验证配置"""
        errors = []
        warnings = []
        
        env = self.load_env()
        
        # 检查域名
        if env['DOMAIN'] == 'your-domain.com':
            warnings.append("⚠️  域名使用默认值，请在 .env 中设置真实域名")
        
        # 检查 V2Ray 配置
        try:
            config = self.load_v2ray_config()
            users = self.get_users()
            
            if not users:
                errors.append("❌ V2Ray 配置中没有用户")
            else:
                print(f"✅ 找到 {len(users)} 个用户配置")
            
            # 检查路径是否匹配
            for inbound in config.get('inbounds', []):
                if inbound.get('protocol') == 'vless':
                    ws_path = inbound.get('streamSettings', {}).get('wsSettings', {}).get('path', '')
                    expected_path = f"/{env['SECRET_PATH']}"
                    
                    if ws_path != expected_path:
                        warnings.append(f"⚠️  V2Ray 路径不匹配: {ws_path} != {expected_path}")
        
        except Exception as e:
            errors.append(f"❌ V2Ray 配置错误: {e}")
        
        # 输出结果
        for warning in warnings:
            print(warning)
        
        for error in errors:
            print(error)
        
        return len(errors) == 0
    
    def display_info(self):
        """显示配置信息"""
        env = self.load_env()
        
        print("\n" + "=" * 70)
        print("🚀 Avalon Tunnel 配置信息")
        print("=" * 70)
        print(f"\n📍 域名: {env['DOMAIN']}")
        print(f"🔐 秘密路径: /{env['SECRET_PATH']}")
        
        users = self.get_users()
        print(f"\n👥 用户数量: {len(users)}")
        
        print("\n" + "=" * 70)
        print("🔗 VLESS 配置链接（复制粘贴到 V2Box）")
        print("=" * 70)
        
        links = self.generate_all_links()
        for i, link_info in enumerate(links, 1):
            print(f"\n【用户 {i}】{link_info['email']}")
            print("-" * 70)
            print(f"UUID: {link_info['uuid']}")
            print(f"\n一键导入链接:")
            print(f"{link_info['link']}")
            print()
        
        print("=" * 70)
        print("📱 使用方法")
        print("=" * 70)
        print("1. 复制上面的 vless:// 开头的完整链接")
        print("2. 打开 V2Box 或 V2RayN")
        print("3. 点击右上角 + 号")
        print("4. 选择 '从剪贴板导入'")
        print("5. 连接并测试")
        print()
    
    def save_links_to_file(self, output_file: str = "v2ray-links.txt"):
        """保存链接到文件"""
        env = self.load_env()
        links = self.generate_all_links()
        
        output_path = self.base_dir / output_file
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("Avalon Tunnel - V2Ray 配置链接\n")
            f.write("=" * 70 + "\n\n")
            f.write(f"域名: {env['DOMAIN']}\n")
            f.write(f"路径: /{env['SECRET_PATH']}\n\n")
            
            for i, link_info in enumerate(links, 1):
                f.write(f"【用户 {i}】{link_info['email']}\n")
                f.write("-" * 70 + "\n")
                f.write(f"UUID: {link_info['uuid']}\n")
                f.write(f"一键导入链接:\n{link_info['link']}\n\n")
            
            f.write("=" * 70 + "\n")
            f.write("手动配置参数\n")
            f.write("=" * 70 + "\n")
            f.write(f"地址: {env['DOMAIN']}\n")
            f.write(f"端口: 443\n")
            f.write(f"传输协议: WebSocket (ws)\n")
            f.write(f"路径: /{env['SECRET_PATH']}\n")
            f.write(f"TLS: 开启\n")
            f.write(f"SNI: {env['DOMAIN']}\n")
        
        print(f"✅ 配置链接已保存到: {output_path}")


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Avalon Tunnel 配置管理器')
    parser.add_argument('action', choices=['validate', 'links', 'sync', 'info'],
                       help='操作: validate(验证配置) | links(生成链接) | sync(同步配置) | info(显示信息)')
    
    args = parser.parse_args()
    
    manager = ConfigManager()
    
    try:
        if args.action == 'validate':
            print("🔍 验证配置...")
            # 先同步配置
            manager.sync_config()
            # 再验证
            if manager.validate_config():
                print("\n✅ 配置验证通过！")
                sys.exit(0)
            else:
                print("\n❌ 配置验证失败！")
                sys.exit(1)
        
        elif args.action == 'links':
            print("🔗 生成配置链接...")
            manager.display_info()
            manager.save_links_to_file()
        
        elif args.action == 'sync':
            manager.sync_config()
        
        elif args.action == 'info':
            manager.display_info()
    
    except Exception as e:
        print(f"❌ 错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main()
