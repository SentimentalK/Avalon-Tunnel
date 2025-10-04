#!/bin/bash

# Avalon Tunnel - UUID 生成脚本
# 用于生成 V2Ray 用户认证所需的 UUID

set -e

echo "🔑 生成 Avalon Tunnel 用户 UUID..."
echo ""

# 检查是否有 uuidgen 命令
if command -v uuidgen >/dev/null 2>&1; then
    echo "使用 uuidgen 生成 UUID："
    for i in {1..3}; do
        uuid=$(uuidgen)
        echo "用户 $i: $uuid"
    done
elif command -v python3 >/dev/null 2>&1; then
    echo "使用 Python 生成 UUID："
    for i in {1..3}; do
        uuid=$(python3 -c "import uuid; print(uuid.uuid4())")
        echo "用户 $i: $uuid"
    done
else
    echo "❌ 错误：未找到 uuidgen 或 python3 命令"
    echo "请安装 uuid-runtime 或 python3"
    exit 1
fi

echo ""
echo "📝 使用说明："
echo "1. 复制上述 UUID 到 config.json 文件中的 clients 部分"
echo "2. 每个用户需要唯一的 UUID"
echo "3. 建议定期更换 UUID 以提高安全性"
echo ""
echo "🔧 配置示例："
echo '{'
echo '  "clients": ['
echo '    {'
echo '      "id": "你的-UUID-1",'
echo '      "level": 0,'
echo '      "email": "user1@example.com"'
echo '    }'
echo '  ]'
echo '}'
