#!/usr/bin/env python3
"""
Avalon Tunnel - 配置管理服务
负责：初始化数据库 → 生成配置文件
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Database
from app.services import ConfigService


class AvalonTunnelManager:
    """Avalon Tunnel 配置管理器"""
    
    def __init__(self, base_dir: str = "/app/config"):
        """
        初始化管理器
        
        Args:
            base_dir: 项目根目录（在容器内是 /app/config）
        """
        self.base_dir = Path(base_dir)
        
        # 初始化各个模块
        self.db = Database(str(self.base_dir / "data" / "avalon.db"))
        self.config_service = ConfigService(str(self.base_dir))
    
    def print_header(self):
        """打印启动横幅"""
        print("\n" + "=" * 70)
        print("🚀 Avalon Tunnel - 配置生成服务")
        print("=" * 70)
        print()
    
    def check_prerequisites(self) -> bool:
        """
        检查前置条件（.env 已在 Makefile 检查过）
        
        Returns:
            是否满足前置条件
        """
        print("📋 阶段 1: 环境检查")
        print("-" * 70)
        
        domain = os.getenv('DOMAIN', 'your-domain.com')
        print(f"✅ 域名: {domain}")
        print()
        
        return True
    
    def initialize_system(self) -> bool:
        """
        初始化系统（首次部署时）
        
        Returns:
            是否成功初始化
        """
        print("📦 阶段 2: 系统初始化")
        print("-" * 70)
        
        # 检查是否已初始化
        if self.db.is_initialized():
            print("✅ 系统已初始化，跳过初始化步骤")
            print()
            return True
        
        print("🔧 首次部署检测到，开始初始化...")
        
        try:
            # 1. 生成秘密路径
            secret_path = ConfigService.generate_secret_path(32)
            self.db.set_setting('secret_path', secret_path, 'V2Ray WebSocket 秘密路径')
            print(f"  ✅ 生成秘密路径: {secret_path[:16]}...{secret_path[-8:]}")
            
            # 2. 创建默认用户
            default_user = self.db.create_user(
                email="default@avalon-tunnel.com",
                notes="系统默认用户（首次部署自动创建）"
            )
            print(f"  ✅ 创建默认用户: {default_user['email']}")
            print(f"     UUID: {default_user['uuid']}")
            
            # 3. 标记为已初始化
            self.db.mark_as_initialized()
            print("  ✅ 系统初始化完成")
            print()
            
            return True
        
        except Exception as e:
            print(f"❌ 初始化失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def generate_configs(self) -> bool:
        """
        生成配置文件
        
        Returns:
            是否成功生成配置
        """
        print("⚙️  阶段 3: 配置文件生成")
        print("-" * 70)
        
        try:
            # 从环境变量和数据库读取配置
            domain = os.getenv('DOMAIN', 'your-domain.com')
            secret_path = self.db.get_setting('secret_path')
            v2ray_port = int(self.db.get_setting('v2ray_port') or 10000)
            
            # 获取所有启用的用户
            users = self.db.get_all_users(enabled_only=True)
            
            if not users:
                print("⚠️  警告: 没有启用的用户，将生成空配置")
            
            # 生成配置文件
            self.config_service.sync_all_configs(
                domain=domain,
                users=users,
                secret_path=secret_path,
                v2ray_port=v2ray_port
            )
            
            print()
            return True
        
        except Exception as e:
            print(f"❌ 配置生成失败: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def display_summary(self):
        """显示配置生成摘要"""
        print("\n" + "=" * 70)
        print("📊 配置生成完成")
        print("=" * 70)
        
        domain = os.getenv('DOMAIN', 'your-domain.com')
        secret_path = self.db.get_setting('secret_path')
        users = self.db.get_all_users(enabled_only=True)
        
        print(f"\n🌐 域名: {domain}")
        print(f"🔐 秘密路径: /{secret_path}")
        print(f"👥 启用用户: {len(users)}")
        
        if users:
            print(f"\n🔗 客户端连接信息:")
            print("-" * 70)
            for user in users:
                link = self.config_service.generate_vless_link(
                    uuid=user['uuid'],
                    domain=domain,
                    secret_path=secret_path,
                    email=user['email']
                )
                print(f"\n📧 {user['email']}")
                print(f"🆔 {user['uuid']}")
                print(f"{link}")
        
        print("\n" + "=" * 70)
        print("✅ 配置已生成")
        print("=" * 70)
        print()
    
    def run(self) -> int:
        """
        运行配置生成流程
        
        Returns:
            退出码 (0: 成功, 非0: 失败)
        """
        self.print_header()
        
        # 阶段 1: 前置条件检查
        if not self.check_prerequisites():
            return 1
        
        # 阶段 2: 系统初始化
        if not self.initialize_system():
            return 1
        
        # 阶段 3: 配置文件生成
        if not self.generate_configs():
            return 1
        
        # 显示总结
        self.display_summary()
        
        return 0


def main():
    """主函数"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Avalon Tunnel - 智能配置与诊断系统'
    )
    parser.add_argument(
        '--base-dir',
        default='/app/config',
        help='项目根目录 (默认: /app/config)'
    )
    
    args = parser.parse_args()
    
    try:
        manager = AvalonTunnelManager(args.base_dir)
        exit_code = manager.run()
        sys.exit(exit_code)
    
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        sys.exit(130)
    
    except Exception as e:
        print(f"\n❌ 致命错误: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

