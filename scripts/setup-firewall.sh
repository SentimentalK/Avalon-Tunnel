#!/bin/bash

# Avalon Tunnel - 防火墙配置脚本 (V3 - 简洁 Docker 兼容版)
# 重置防火墙，开放22/80/443端口，设置Docker NAT与转发（专注IPv4）

set -e

echo "🔥 配置 Avalon Tunnel 防火墙 (Docker 兼容版 V3)..."

echo "⚠️  重置现有防火墙规则..."
ufw --force reset

echo "📋 设置默认防火墙策略..."
ufw default deny incoming
ufw default allow outgoing

# 配置 Docker forwarding policy
if [ -f /etc/default/ufw ]; then
    sed -i 's/DEFAULT_FORWARD_POLICY="DROP"/DEFAULT_FORWARD_POLICY="ACCEPT"/' /etc/default/ufw
    echo "   ✅ 已将默认转发策略设置为 ACCEPT"
else
    echo "   ⚠️  警告：未找到 /etc/default/ufw 文件"
fi

# 添加 Docker NAT 规则（IPv4，只加 MASQUERADE）
UFW_BEFORE_RULES="/etc/ufw/before.rules"
if [ -f "$UFW_BEFORE_RULES" ]; then
    if ! grep -q "DOCKER NAT rules" "$UFW_BEFORE_RULES"; then
        echo "   🔧 添加 Docker NAT 规则到 UFW..."
        cp "$UFW_BEFORE_RULES" "${UFW_BEFORE_RULES}.backup.$(date +%Y%m%d_%H%M%S)"
        {
            echo "# BEGIN DOCKER NAT rules"
            echo "*nat"
            echo ":POSTROUTING ACCEPT [0:0]"
            echo "# 允许 Docker 容器访问外网"
            echo "-A POSTROUTING -s 172.16.0.0/12 -j MASQUERADE"
            echo "-A POSTROUTING -s 192.168.0.0/16 -j MASQUERADE"
            echo "COMMIT"
            echo "# END DOCKER NAT rules"
        } >> "$UFW_BEFORE_RULES"
        echo "   ✅ Docker NAT 规则已添加"
    else
        echo "   ℹ️  Docker NAT 规则已存在"
    fi
fi

echo "   🔧 启用内核 IP 转发（IPv4）..."
sysctl -w net.ipv4.ip_forward=1 > /dev/null

# 永久启用 IP 转发（IPv4）
if [ -f /etc/sysctl.conf ]; then
    if ! grep -q '^net.ipv4.ip_forward=1' /etc/sysctl.conf; then
        echo 'net.ipv4.ip_forward=1' >> /etc/sysctl.conf
        echo "   ✅ IP 转发已永久启用"
    fi
fi

# 开放端口22,80,443
ufw allow 22/tcp comment 'SSH access'
ufw allow 80/tcp comment 'HTTP for TLS certificate'
ufw allow 443/tcp comment 'HTTPS main service'

# 启用防火墙
ufw --force enable

echo "📊 防火墙状态："
ufw status verbose

cat << EOF

✅ 防火墙配置完成！
开放端口: 22/80/443
Docker 网络转发和 NAT 已配置（IPv4）

下一步:
  sudo systemctl restart docker
  # 清理后重测容器网络
  sudo docker run --rm alpine sh -c 'apk add --no-cache curl && curl -I https://www.google.com'

EOF
