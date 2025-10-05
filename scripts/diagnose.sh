#!/bin/bash

#=================================================================================
# Avalon Tunnel - 全链路自动化诊断脚本
#
# 功能:
#   - 检查域名解析与公网 IP 是否匹配
#   - 检查主机与容器的网络连接和 DNS
#   - 检查防火墙设置 (UFW 和云服务商安全组)
#   - 检查 Docker 服务和核心容器的运行状态
#   - 执行端到端的应用层连接测试，模拟真实客户端
#
# 使用:
#   1. 将此脚本放置在 docker-compose.yml 同级目录下
#   2. chmod +x diagnose.sh
#   3. sudo ./diagnose.sh
#
#=================================================================================

# --- 配置 ---
# 从 .env 文件加载配置, 如果不存在则使用默认值
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi
DOMAIN=${DOMAIN:-"your-domain.com"}
SECRET_PATH=${SECRET_PATH:-"avalon-secret-path"}
V2RAY_PORT=${V2RAY_PORT:-10000} # V2Ray 在 Caddyfile 中配置的内部端口

# --- 颜色定义 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# --- 辅助函数 ---
print_info() {
  echo -e "${YELLOW}INFO: $1${NC}"
}
print_success() {
  echo -e "${GREEN}✅ PASS:${NC} $1"
}
print_fail() {
  echo -e "${RED}❌ FAIL:${NC} $1"
  FAIL_COUNT=$((FAIL_COUNT + 1))
}

check_command() {
  if ! command -v $1 &> /dev/null; then
    print_fail "必需命令 '$1' 未找到。请先安装 (例如: sudo apt update && sudo apt install -y $2)"
    exit 1
  fi
}

# --- 初始化 ---
FAIL_COUNT=0
clear
echo "=============================================="
echo "    🚀 Avalon Tunnel 全链路诊断开始 🚀"
echo "=============================================="
echo "将要测试的域名: $DOMAIN"
echo "将要测试的路径: /$SECRET_PATH"
echo ""

# --- 阶段 1: 环境与前置检查 ---
echo "--- 阶段 1: 环境与前置检查 ---"
if [ "$EUID" -ne 0 ]; then
  print_fail "此脚本需要 root 权限 (sudo) 才能执行网络和 Docker 的深度检查。"
  exit 1
else
  print_success "以 root 权限运行。"
fi

check_command "docker" "docker.io"
check_command "dig" "dnsutils"
check_command "nc" "netcat"
check_command "curl" "curl"
echo ""

# --- 阶段 2: 域名解析与主机网络 ---
echo "--- 阶段 2: 域名解析与主机网络 ---"
PUBLIC_IP=$(dig +short myip.opendns.com @resolver1.opendns.com)
if [ -z "$PUBLIC_IP" ]; then
  PUBLIC_IP=$(curl -s ifconfig.me)
fi

if [ -z "$PUBLIC_IP" ]; then
  print_fail "无法获取服务器的公网 IP 地址。请检查主机的网络连接。"
else
  print_success "获取到公网 IP: $PUBLIC_IP"
fi

DOMAIN_IP=$(dig +short $DOMAIN | head -n 1)
if [ -z "$DOMAIN_IP" ]; then
  print_fail "无法解析域名 '$DOMAIN'。请检查你的 DNS 配置是否正确且已生效。"
else
  print_success "域名 '$DOMAIN' 解析到 IP: $DOMAIN_IP"
  if [ "$PUBLIC_IP" == "$DOMAIN_IP" ]; then
    print_success "域名解析的 IP 与本机公网 IP 匹配。"
  else
    print_fail "域名解析 IP ($DOMAIN_IP) 与本机公网 IP ($PUBLIC_IP) 不匹配！"
  fi
fi

if ping -c 1 8.8.8.8 &> /dev/null; then
  print_success "主机可以访问外部网络 (ping 8.8.8.8)。"
else
  print_fail "主机无法访问外部网络。请检查主机的路由表或网络配置。"
fi
echo ""

# --- 阶段 3: 防火墙与端口检查 ---
echo "--- 阶段 3: 防火墙与端口检查 ---"
# 检查本地 UFW 防火墙
if ufw status | grep -qw active; then
  print_info "检测到 UFW 防火墙处于活动状态。"
  if ufw status | grep -q "443/tcp" | grep -q "ALLOW"; then
    print_success "UFW 防火墙允许 443/tcp 端口的入站流量。"
  else
    print_fail "UFW 防火墙未明确允许 443/tcp 端口。请运行 'sudo ufw allow 443/tcp'。"
  fi
else
  print_info "UFW 防火墙未激活。请注意检查云服务商的安全组。"
fi

# 检查端口是否被 Docker 监听
if ss -tlpn | grep -q 'docker-proxy.*:443'; then
  print_success "端口 443 正在被 Docker 监听，服务已暴露。"
else
  print_fail "端口 443 未被 Docker 监听。请检查 Caddy 容器是否正常启动且使用了 'host' 网络模式或正确的端口映射。"
fi

# 模拟外部访问，检测云服务商防火墙 (VPC/安全组)
print_info "正在尝试从本机通过公网 IP 连接 443 端口 (模拟外部访问)..."
if nc -z -w 5 $PUBLIC_IP 443; then
  print_success "成功连接到公网 IP 的 443 端口。云服务商防火墙/安全组配置正确。"
else
  print_fail "无法从本机通过公网 IP 连接到 443 端口。这极有可能意味着云服务商的防火墙 (安全组/VPC规则) 阻止了外部访问。"
fi
echo ""


# --- 阶段 4: Docker 容器健康检查 ---
echo "--- 阶段 4: Docker 容器健康检查 ---"
if ! docker info &> /dev/null; then
  print_fail "Docker 守护进程未运行或当前用户无权限访问。"
  exit 1
fi

CADDY_RUNNING=$(docker ps -q -f name=avalon-caddy)
V2RAY_RUNNING=$(docker ps -q -f name=avalon-v2ray)

if [ -n "$CADDY_RUNNING" ]; then
  print_success "Caddy 容器 (avalon-caddy) 正在运行。"
else
  print_fail "Caddy 容器 (avalon-caddy) 未运行。请检查 'docker compose logs caddy'。 "
fi

if [ -n "$V2RAY_RUNNING" ]; then
  print_success "V2Ray 容器 (avalon-v2ray) 正在运行。"
else
  print_fail "V2Ray 容器 (avalon-v2ray) 未运行。请检查 'docker compose logs v2ray'。"
fi

if [ -n "$V2RAY_RUNNING" ]; then
  if docker exec $V2RAY_RUNNING nslookup google.com &> /dev/null; then
    print_success "V2Ray 容器内 DNS 解析正常。"
  else
    print_fail "V2Ray 容器内 DNS 解析失败！这是我们之前遇到的问题，请检查 docker-compose.yml 中是否为 v2ray 服务添加了公共 DNS (如 8.8.8.8)。"
  fi
fi
echo ""


# --- 阶段 5: 端到端应用链路测试 ---
echo "--- 阶段 5: 端到端应用链路测试 ---"
print_info "正在启动一个临时容器，模拟真实客户端发起 WebSocket 连接测试..."

# 使用一个包含 curl 的轻量级镜像
TEST_IMAGE="curlimages/curl:latest"
docker pull $TEST_IMAGE > /dev/null

# 执行 curl 测试命令
# -k: 忽略证书验证，因为我们是从容器内部访问，证书可能不匹配 localhost
# --resolve: 强制将域名解析到 127.0.0.1，这样可以直接测试本地 Caddy 服务
# 这样可以同时测试 Caddy 的域名配置和到 V2Ray 的反向代理
CURL_OUTPUT=$(docker run --rm --network host $TEST_IMAGE \
  curl -L --http1.1 \
  -H "Upgrade: websocket" \
  -H "Connection: Upgrade" \
  -H "Host: $DOMAIN" \
  --head \
  --max-time 10 \
  "https://127.0.0.1/$SECRET_PATH")

if echo "$CURL_OUTPUT" | grep -q "HTTP/1.1 101 Switching Protocols"; then
  print_success "端到端链路测试成功！Caddy 成功接收请求并将其升级为 WebSocket 转发给了 V2Ray。"
else
  print_fail "端到端链路测试失败！请求未能从 Caddy 正确转发到 V2Ray。"
  print_info "Caddy 返回的头信息如下:"
  echo "$CURL_OUTPUT"
fi
echo ""


# --- 总结报告 ---
echo "=============================================="
echo "                📊 诊断完成 📊"
echo "=============================================="
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo -e "${GREEN}🎉 恭喜！所有诊断项目均已通过。你的 Avalon Tunnel 部署看起来非常健康！${NC}"
else
  echo -e "${RED}发现 ${FAIL_COUNT} 个问题。请向上滚动查看标记为 [❌ FAIL] 的项目及其修复建议。${NC}"
fi
echo "=============================================="

exit $FAIL_COUNT
