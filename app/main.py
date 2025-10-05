#!/usr/bin/env python3
"""
Avalon Tunnel - 主入口程序
负责编排整个启动流程：初始化 → 配置生成 → 诊断 → 启动服务
"""

import os
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.database import Database
from app.services import ConfigService
from app.diagnostics import DiagnosticService


class AvalonTunnelManager:
    """Avalon Tunnel 管理器 - 系统的大脑"""
    
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
        self.diagnostic_service = DiagnosticService(str(self.base_dir))
    
    def print_header(self):
        """打印启动横幅"""
        print("\n" + "=" * 70)
        print("🚀 Avalon Tunnel - 智能配置与诊断系统")
        print("=" * 70)
        print()
    
    def check_prerequisites(self) -> bool:
        """
        检查前置条件
        
        Returns:
            是否满足前置条件
        """
        print("📋 阶段 1: 前置条件检查")
        print("-" * 70)
        
        # 检查 .env 文件
        env_file = self.base_dir / ".env"
        if not env_file.exists():
            print("❌ 错误: .env 文件不存在")
            print("   请复制 env.example 为 .env 并配置您的域名:")
            print(f"   cp {self.base_dir}/env.example {self.base_dir}/.env")
            return False
        
        print(f"✅ 找到配置文件: .env")
        
        # 检查域名配置
        domain = os.getenv('DOMAIN', '')
        if not domain or domain == 'your-domain.com':
            print("❌ 错误: 未配置域名")
            print("   请在 .env 文件中设置 DOMAIN 为您的真实域名")
            return False
        
        print(f"✅ 域名配置: {domain}")
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
    
    def run_diagnostics(self) -> bool:
        """
        运行全链路诊断
        
        Returns:
            诊断是否通过
        """
        print("🔍 阶段 4: 全链路诊断")
        print("-" * 70)
        print()
        
        # 获取配置参数
        domain = os.getenv('DOMAIN', 'your-domain.com')
        secret_path = self.db.get_setting('secret_path')
        v2ray_port = int(self.db.get_setting('v2ray_port') or 10000)
        
        # 运行诊断
        success, output = self.diagnostic_service.run_diagnostics(
            domain=domain,
            secret_path=secret_path,
            v2ray_port=v2ray_port,
            realtime_output=True
        )
        
        return success
    
    def display_summary(self, success: bool):
        """
        显示部署总结
        
        Args:
            success: 是否部署成功
        """
        print("\n" + "=" * 70)
        print("📊 部署总结")
        print("=" * 70)
        
        if success:
            print("✅ 所有检查通过，准备启动核心服务...")
            print()
            
            # 显示用户连接信息
            domain = os.getenv('DOMAIN', 'your-domain.com')
            secret_path = self.db.get_setting('secret_path')
            users = self.db.get_all_users(enabled_only=True)
            
            print(f"🌐 服务地址: https://{domain}")
            print(f"🔐 秘密路径: /{secret_path}")
            print(f"👥 启用用户: {len(users)}")
            print()
            
            print("🔗 客户端连接链接:")
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
                print(f"🔗 {link}")
            
            print()
            print("=" * 70)
            print("✅ Manager 服务完成，Docker Compose 将启动 V2Ray 和 Caddy")
            print("=" * 70)
        
        else:
            print("❌ 检查失败，服务不会启动")
            print()
            print("🔧 请根据上方的错误信息进行修复，然后重新运行:")
            print("   docker compose up --force-recreate")
            print()
            print("=" * 70)
    
    def run(self) -> int:
        """
        运行完整的启动流程
        
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
        
        # 阶段 4: 全链路诊断
        diagnostic_passed = self.run_diagnostics()
        
        # 显示总结
        self.display_summary(diagnostic_passed)
        
        # 返回退出码
        return 0 if diagnostic_passed else 1


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
    parser.add_argument(
        '--skip-diagnostics',
        action='store_true',
        help='跳过诊断步骤（仅用于调试）'
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

