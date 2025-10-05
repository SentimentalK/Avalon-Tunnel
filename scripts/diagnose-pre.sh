#!/bin/bash

#=================================================================================
# Avalon Tunnel - 环境预检查脚本
# 在 docker compose up 之前运行，确保基础环境满足要求
#=================================================================================

# --- 配置 ---
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi
DOMAIN=${DOMAIN:-"your-domain.com"}

# --- 颜色定义 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[1;34m'
NC='\033[0m'

# --- 辅助函数 ---
print_info() { echo -e "${YELLOW}INFO: $1${NC}"; }
print_success() { echo -e "${GREEN}✅ PASS:${NC} $1"; }
print_fail() { echo -e "${RED}❌ FAIL:${NC} $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }
print_warning() { echo -e "${YELLOW}⚠️  WARN:${NC} $1"; }

check_command() {
  if ! command -v $1 &> /dev/null; then
    print_fail "必需命令 '$1' 未找到。请先安装: sudo apt install -y $2"
    exit 1
  fi
}

# 检测 IP 是否为 IPv6
is_ipv6() {
  [[ "$1" =~ : ]]
}

# --- 初始化 ---
FAIL_COUNT=0
clear
echo "=============================================="
echo "    🔍 Avalon Tunnel 环境预检查"
echo "=============================================="
echo "域名: $DOMAIN"
echo ""

# --- 阶段 1: 权限与命令检查 ---
echo "--- 阶段 1: 权限与命令检查 ---"
if [ "$EUID" -ne 0 ]; then
  print_fail "此脚本需要 root 权限 (sudo)。"
  exit 1
else
  print_success "以 root 权限运行。"
fi

check_command "docker" "docker.io"
check_command "dig" "dnsutils"
check_command "nc" "netcat-traditional"
check_command "curl" "curl"
check_command "python3" "python3"
echo ""

# --- 阶段 2: 网络连通性 ---
echo "--- 阶段 2: 网络连通性 ---"

# 获取公网 IP（支持 IPv6）
PUBLIC_IP=$(curl -6 -s --max-time 5 https://api6.ipify.org 2>/dev/null)
if [ -z "$PUBLIC_IP" ]; then
  PUBLIC_IP=$(curl -4 -s --max-time 5 https://api.ipify.org 2>/dev/null)
fi

if [ -z "$PUBLIC_IP" ]; then
  print_fail "无法获取服务器的公网 IP 地址。请检查网络连接。"
else
  if is_ipv6 "$PUBLIC_IP"; then
    print_success "获取到公网 IPv6: $PUBLIC_IP"
  else
    print_success "获取到公网 IPv4: $PUBLIC_IP"
  fi
fi

# 域名解析（支持 IPv6）
DOMAIN_IP=$(dig +short $DOMAIN AAAA | head -n 1)
if [ -z "$DOMAIN_IP" ]; then
  DOMAIN_IP=$(dig +short $DOMAIN A | head -n 1)
fi

if [ -z "$DOMAIN_IP" ]; then
  print_fail "无法解析域名 '$DOMAIN'。请检查 DNS 配置。"
else
  if is_ipv6 "$DOMAIN_IP"; then
    print_success "域名 '$DOMAIN' 解析到 IPv6: $DOMAIN_IP"
  else
    print_success "域名 '$DOMAIN' 解析到 IPv4: $DOMAIN_IP"
  fi
  
  # 检查 IP 是否匹配（仅提示，不强制）
  if [ "$PUBLIC_IP" == "$DOMAIN_IP" ]; then
    print_success "域名 IP 与本机公网 IP 完全匹配。"
  else
    print_warning "域名 IP ($DOMAIN_IP) 与本机公网 IP ($PUBLIC_IP) 不同。"
    print_info "如果你使用 CDN 或代理，这是正常的。否则请检查 DNS 配置。"
  fi
fi

# 测试外网连通性（优先 IPv6）
if curl -6 -s --max-time 5 https://www.google.com > /dev/null 2>&1; then
  print_success "可以通过 IPv6 访问外部网络。"
elif curl -4 -s --max-time 5 https://www.google.com > /dev/null 2>&1; then
  print_success "可以通过 IPv4 访问外部网络。"
else
  print_fail "无法访问外部网络。请检查路由和 DNS 配置。"
fi
echo ""

# --- 阶段 3: 防火墙检查 ---
echo "--- 阶段 3: 本地防火墙 (UFW) 检查 ---"

if ! command -v ufw &> /dev/null; then
  print_warning "未检测到 UFW。如果你在使用其他防火墙，请手动确认已开放 22/80/443 端口。"
else
  if ufw status | grep -qw active; then
    print_info "UFW 防火墙处于活动状态。"
    
    # 检查端口 443
    if ufw status | grep -E "443.*ALLOW" > /dev/null; then
      print_success "UFW 已允许 443/tcp 端口。"
    else
      print_fail "UFW 未允许 443/tcp 端口。防火墙脚本可能未正确执行。"
    fi
    
    # 检查端口 80（用于 TLS 证书申请）
    if ufw status | grep -E "80.*ALLOW" > /dev/null; then
      print_success "UFW 已允许 80/tcp 端口。"
    else
      print_warning "UFW 未允许 80/tcp 端口。Caddy 自动申请证书可能失败。"
    fi
  else
    print_warning "UFW 防火墙未激活。请确保云服务商安全组已正确配置。"
  fi
fi
echo ""

# --- 阶段 4: Oracle Cloud VCN 安全组检查 ---
echo "--- 阶段 4: Oracle Cloud VCN 安全组检查 ---"
print_info "Oracle Cloud 使用双层防火墙：UFW（主机级）+ VCN Security List（网络级）"
print_info "即使 UFW 开放了端口，VCN Security List 也必须允许入站流量！"
echo ""
echo -e "${BLUE}请手动检查以下配置：${NC}"
echo "1. 登录 Oracle Cloud Console"
echo "2. 进入：Networking -> Virtual Cloud Networks -> 你的 VCN"
echo "3. 点击：Security Lists -> Default Security List"
echo "4. 检查 Ingress Rules 是否包含："
echo "   - Source: 0.0.0.0/0，Dest Port: 443，Protocol: TCP"
echo "   - Source: 0.0.0.0/0，Dest Port: 80，Protocol: TCP"
echo "   - Source: ::/0，Dest Port: 443，Protocol: TCP（如果使用 IPv6）"
echo "   - Source: ::/0，Dest Port: 80，Protocol: TCP（如果使用 IPv6）"
echo ""
print_warning "如果没有这些规则，请在 Oracle Cloud Console 中添加！"
echo ""

# --- 阶段 5: Docker 检查 ---
echo "--- 阶段 5: Docker 服务检查 ---"
if ! docker info &> /dev/null; then
  print_fail "Docker 守护进程未运行或当前用户无权限访问。"
  exit 1
else
  print_success "Docker 服务运行正常。"
fi

# 检查 Docker 网络
if docker network ls | grep -q bridge; then
  print_success "Docker 默认网络配置正常。"
fi
echo ""

# --- 总结 ---
echo "=============================================="
echo "            📊 预检查完成"
echo "=============================================="
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo -e "${GREEN}✅ 所有预检查项目均通过！可以启动服务。${NC}"
else
  echo -e "${RED}发现 ${FAIL_COUNT} 个问题。请修复后再启动服务。${NC}"
fi
echo "=============================================="

exit $FAIL_COUNT

# --- 检查 DNS64 配置 ---
echo "--- DNS64/NAT64 配置检查（IPv6-only 环境必需）---"
if is_ipv6 "$PUBLIC_IP"; then
  print_info "检测到 IPv6-only 环境，检查 DNS64 配置..."
  
  # 检查 DNS64 配置
  if grep -r "2606:4700:4700::64\|2001:4860:4860::6464\|2a01:4f9:c010:3f02::1" /etc/systemd/resolved.conf* 2>/dev/null; then
    print_success "已配置 DNS64 服务。"
  else
    print_warning "未检测到 DNS64 配置。"
    print_info "IPv6-only 服务器需要 DNS64 才能访问 IPv4-only 网站（如 GitHub）。"
    print_info "运行 'make setup' 自动配置。"
  fi
  
  # 测试能否访问 IPv4-only 网站
  print_info "测试访问 IPv4-only 网站（github.com）..."
  if curl -6 -s --max-time 5 https://github.com > /dev/null 2>&1; then
    print_success "可以访问 IPv4-only 网站。NAT64/DNS64 工作正常。"
  else
    print_fail "无法访问 IPv4-only 网站！"
    print_info "这意味着你的代理客户端将无法访问大量网站（约 57%）。"
    print_info "请配置 DNS64/NAT64 服务。"
  fi
fi
echo ""
