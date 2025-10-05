#!/bin/bash

#=================================================================================
# Avalon Tunnel - 重启 V2Ray 容器
# 用于 API 调用配置重载后重启 V2Ray
#=================================================================================

set -e

echo "🔄 重启 V2Ray 容器..."

# 重启 V2Ray
if docker restart avalon-v2ray &> /dev/null; then
    echo "✅ V2Ray 已重启"
    exit 0
else
    echo "❌ V2Ray 重启失败"
    exit 1
fi
