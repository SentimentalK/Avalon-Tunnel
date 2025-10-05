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
            # 1. 检查默认用户
            morgan_user = self.db.get_user_by_email('Morgan@avalon-tunnel.com')
            
            if not morgan_user:
                print(f"  ❌ 错误: 默认用户未找到（数据库初始化可能异常）")
                return False
            
            # 2. 检查是否已有秘密路径（如果有，说明之前已初始化过）
            if not morgan_user['secret_path'] or morgan_user['secret_path'] == '':
                # 首次初始化：生成秘密路径
                secret_path = ConfigService.generate_secret_path(32)
                self.db.update_user(morgan_user['uuid'], secret_path=secret_path)
                print(f"  ✅ 为默认用户生成秘密路径: /{secret_path[:16]}...{secret_path[-8:]}")
                print(f"  💡 此路径将永久保存，重建容器不会改变")
            else:
                # 已有路径：跳过生成
                print(f"  ✅ 默认用户已有秘密路径（复用）: /{morgan_user['secret_path'][:16]}...")
                print(f"  💡 路径未改变，客户端无需更新配置")
            
            # 3. 显示默认用户信息
            morgan_user = self.db.get_user_by_email('Morgan@avalon-tunnel.com')  # 重新获取
            print(f"  ✅ 默认用户已就绪: {morgan_user['email']}")
            print(f"     UUID: {morgan_user['uuid']}")
            
            # 4. 清理旧的全局 secret_path 设置（Phase 1 遗留）
            self.db.set_setting('secret_path', '', '已弃用 - 改为每用户独立路径')
            
            # 5. 标记为已初始化
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
            v2ray_port = int(self.db.get_setting('v2ray_port') or 10000)
            
            # 获取所有启用的用户（每个用户有自己的 secret_path）
            users = self.db.get_all_users(enabled_only=True)
            
            if not users:
                print("⚠️  警告: 没有启用的用户，将生成空配置")
            
            # 生成配置文件（Phase 2: 多用户多路径）
            self.config_service.sync_all_configs(
                domain=domain,
                users=users,
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
        users = self.db.get_all_users(enabled_only=True)
        
        print(f"\n🌐 域名: {domain}")
        print(f"👥 启用用户: {len(users)}")
        
        if users:
            print(f"\n🔗 客户端连接信息:")
            print("-" * 70)
            for user in users:
                link = self.config_service.generate_vless_link(
                    uuid=user['uuid'],
                    domain=domain,
                    secret_path=user['secret_path'],  # 每个用户独立路径
                    email=user['email']
                )
                print(f"\n📧 {user['email']}")
                print(f"🆔 {user['uuid']}")
                print(f"🔐 路径: /{user['secret_path'][:16]}...{user['secret_path'][-8:]}")
                print(f"🔗 {link}")
        
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

