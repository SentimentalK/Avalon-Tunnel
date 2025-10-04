#!/bin/bash

# Avalon Tunnel - 防火墙配置脚本
# 此脚本将配置 UFW 防火墙，只开放必要的端口

set -e

echo "🔥 配置 Avalon Tunnel 防火墙..."

# 重置防火墙规则（谨慎操作）
echo "⚠️  重置现有防火墙规则..."
ufw --force reset

# 设置默认策略
echo "📋 设置默认防火墙策略..."
ufw default deny incoming
ufw default allow outgoing

# 允许 SSH (22端口) - 重要：确保不会锁定自己
echo "🔑 允许 SSH 连接..."
ufw allow 22/tcp comment 'SSH access'

# 允许 HTTP (80端口) - Caddy 证书申请需要
echo "🌐 允许 HTTP 流量..."
ufw allow 80/tcp comment 'HTTP for TLS certificate'

# 允许 HTTPS (443端口) - 主要服务端口
echo "🔒 允许 HTTPS 流量..."
ufw allow 443/tcp comment 'HTTPS main service'

# 允许 IPv6 流量
echo "🌍 配置 IPv6 支持..."
ufw allow from ::/0 to any port 22
ufw allow from ::/0 to any port 80
ufw allow from ::/0 to any port 443

# 启用防火墙
echo "✅ 启用防火墙..."
ufw --force enable

# 显示状态
echo "📊 防火墙状态："
ufw status verbose

echo ""
echo "✅ 防火墙配置完成！"
echo "🔍 开放的端口："
echo "   - 22/tcp  (SSH 管理)"
echo "   - 80/tcp  (HTTP 证书申请)"
echo "   - 443/tcp (HTTPS 主服务)"
echo ""
echo "⚠️  注意：V2Ray 内部端口 (10000) 已被防火墙保护"
echo "🔒 所有其他端口均被阻止，确保服务安全"
