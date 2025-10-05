#!/usr/bin/env python3
"""
Avalon Tunnel - 诊断服务模块
负责调用诊断脚本并解析结果
"""

import subprocess
import sys
from pathlib import Path
from typing import Tuple, Optional


class DiagnosticService:
    """诊断服务 - 调用全链路诊断脚本"""
    
    def __init__(self, base_dir: str = "."):
        """
        初始化诊断服务
        
        Args:
            base_dir: 项目根目录
        """
        self.base_dir = Path(base_dir)
        self.diagnose_script = self.base_dir / "scripts" / "diagnose.sh"
    
    def run_diagnostics(self, domain: str, secret_path: str, 
                       v2ray_port: int = 10000, 
                       realtime_output: bool = True) -> Tuple[bool, str]:
        """
        运行全链路诊断
        
        Args:
            domain: 域名
            secret_path: 秘密路径
            v2ray_port: V2Ray 端口
            realtime_output: 是否实时输出诊断过程
        
        Returns:
            (是否成功, 输出信息)
        """
        if not self.diagnose_script.exists():
            return False, f"诊断脚本不存在: {self.diagnose_script}"
        
        # 设置环境变量
        env = {
            **subprocess.os.environ,
            'DOMAIN': domain,
            'SECRET_PATH': secret_path,
            'V2RAY_PORT': str(v2ray_port)
        }
        
        print("\n" + "=" * 70)
        print("🔍 开始全链路诊断...")
        print("=" * 70)
        
        try:
            if realtime_output:
                # 实时输出模式 - 边运行边打印
                process = subprocess.Popen(
                    ['bash', str(self.diagnose_script)],
                    env=env,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )
                
                output_lines = []
                for line in process.stdout:
                    line = line.rstrip()
                    print(line)
                    output_lines.append(line)
                
                process.wait()
                output = '\n'.join(output_lines)
                success = process.returncode == 0
            else:
                # 静默模式 - 运行完后一次性返回
                result = subprocess.run(
                    ['bash', str(self.diagnose_script)],
                    env=env,
                    capture_output=True,
                    text=True
                )
                
                output = result.stdout + result.stderr
                success = result.returncode == 0
            
            print("=" * 70)
            
            if success:
                print("✅ 诊断完成：所有检查均通过！")
            else:
                print("❌ 诊断完成：发现问题，请查看上方输出")
            
            print("=" * 70)
            print()
            
            return success, output
        
        except FileNotFoundError:
            error_msg = "错误：未找到 bash 命令。请确保系统已安装 bash。"
            print(error_msg)
            return False, error_msg
        
        except Exception as e:
            error_msg = f"运行诊断时发生错误: {str(e)}"
            print(error_msg)
            return False, error_msg
    
    def check_prerequisites(self) -> Tuple[bool, List[str]]:
        """
        检查诊断前置条件
        
        Returns:
            (是否满足条件, 错误信息列表)
        """
        errors = []
        
        # 检查诊断脚本是否存在
        if not self.diagnose_script.exists():
            errors.append(f"诊断脚本不存在: {self.diagnose_script}")
        
        # 检查脚本是否可执行
        elif not self.diagnose_script.stat().st_mode & 0o111:
            errors.append(f"诊断脚本不可执行，请运行: chmod +x {self.diagnose_script}")
        
        # 检查是否有 root 权限
        import os
        if os.geteuid() != 0:
            errors.append("诊断需要 root 权限，请使用 sudo 运行")
        
        return len(errors) == 0, errors


if __name__ == "__main__":
    # 测试诊断服务
    print("🧪 测试诊断服务...")
    
    service = DiagnosticService()
    
    # 检查前置条件
    can_run, errors = service.check_prerequisites()
    if not can_run:
        print("❌ 前置条件检查失败:")
        for error in errors:
            print(f"  - {error}")
    else:
        print("✅ 前置条件检查通过")
    
    print("\n提示: 实际运行诊断需要 sudo 权限和正确的配置")

