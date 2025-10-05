#!/bin/bash

#=================================================================================
# Avalon Tunnel - 服务验证脚本（Phase 2: 多用户支持）
# 在 docker compose up 之后运行，验证服务是否正常工作
#=================================================================================

# --- 配置 ---
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi
DOMAIN=${DOMAIN:-"your-domain.com"}
V2RAY_PORT=${V2RAY_PORT:-10000}

# Phase 2: 从 config.json 读取用户信息（支持多用户）
USER_COUNT=$(python3 -c "
import json
config = json.load(open('config.json'))
clients = config['inbounds'][0]['settings']['clients']
print(len(clients))
" 2>/dev/null)

if [ -z "$USER_COUNT" ] || [ "$USER_COUNT" -eq "0" ]; then
  echo "❌ 错误: config.json 中没有用户配置"
  echo "提示: 请先运行 'make config' 生成配置"
  exit 1
fi

# 读取第一个用户用于测试（通常是 Morgan）
FIRST_USER=$(python3 -c "
import json
config = json.load(open('config.json'))
client = config['inbounds'][0]['settings']['clients'][0]
print(f\"{client['email']}|{client['id']}\")
" 2>/dev/null)

TEST_USER_EMAIL=$(echo "$FIRST_USER" | cut -d'|' -f1)
TEST_USER_UUID=$(echo "$FIRST_USER" | cut -d'|' -f2)

# --- 颜色定义 ---
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# --- 辅助函数 ---
print_info() { echo -e "${YELLOW}INFO: $1${NC}"; }
print_success() { echo -e "${GREEN}✅ PASS:${NC} $1"; }
print_fail() { echo -e "${RED}❌ FAIL:${NC} $1"; FAIL_COUNT=$((FAIL_COUNT + 1)); }

# --- 初始化 ---
FAIL_COUNT=0
echo ""
echo "=============================================="
echo "    🧪 Avalon Tunnel 服务验证"
echo "=============================================="
echo "域名: $DOMAIN"
echo "用户数量: $USER_COUNT"
echo "测试用户: $TEST_USER_EMAIL"
echo "UUID: $TEST_USER_UUID"
echo ""

# --- 检查容器运行状态 ---
echo "--- 容器运行状态 ---"
CADDY_RUNNING=$(docker ps -q -f name=avalon-caddy)
V2RAY_RUNNING=$(docker ps -q -f name=avalon-v2ray)

if [ -n "$CADDY_RUNNING" ]; then
  print_success "Caddy 容器正在运行。"
else
  print_fail "Caddy 容器未运行。请检查: docker compose logs caddy"
fi

if [ -n "$V2RAY_RUNNING" ]; then
  print_success "V2Ray 容器正在运行。"
else
  print_fail "V2Ray 容器未运行。请检查: docker compose logs v2ray"
fi
echo ""

# --- 检查端口监听 ---
echo "--- 端口监听检查 ---"
if ss -tlpn | grep -q ':443'; then
  print_success "端口 443 正在监听。"
else
  print_fail "端口 443 未监听。Caddy 可能未正常启动。"
fi

if ss -tlpn | grep -q ":$V2RAY_PORT"; then
  print_success "V2Ray 端口 $V2RAY_PORT 正在监听。"
else
  print_fail "V2Ray 端口 $V2RAY_PORT 未监听。"
fi
echo ""

# --- 容器网络检查 ---
if [ -n "$V2RAY_RUNNING" ]; then
  echo "--- 容器网络检查 ---"
  
  # 1. DNS 解析测试（默认 DNS）
  if docker exec $V2RAY_RUNNING nslookup google.com &> /dev/null; then
    print_success "V2Ray 容器 DNS 解析正常（默认 DNS）。"
  else
    print_fail "V2Ray 容器 DNS 解析失败（默认 DNS）。"
  fi
  
  # 2. IPv4 DNS 可达性测试（预期：IPv6-only 环境下会失败）
  IPV4_DNS_OK=0
  for dns in "1.1.1.1" "8.8.8.8"; do
    if docker exec $V2RAY_RUNNING nslookup google.com "$dns" &> /dev/null; then
      IPV4_DNS_OK=1
      break
    fi
  done
  
  if [ $IPV4_DNS_OK -eq 1 ]; then
    print_success "V2Ray 容器可以访问 IPv4 DNS 服务器。"
  else
    print_info "V2Ray 容器无法访问 IPv4 DNS（预期行为：IPv6-only 环境）。"
    print_info "V2Ray 已配置使用 localhost 和 DNS64，客户端流量正常。"
  fi
  
  # 3. IPv6 连通性测试
  if docker exec $V2RAY_RUNNING ping6 -c 2 -W 2 2606:4700:4700::1111 &> /dev/null; then
    print_success "V2Ray 容器 IPv6 连通性正常。"
  else
    print_fail "V2Ray 容器无法通过 IPv6 访问外网。"
  fi
  
  # 4. HTTPS 访问测试
  if docker exec $V2RAY_RUNNING wget -O /dev/null --timeout=5 https://www.google.com &> /dev/null; then
    print_success "V2Ray 容器可以访问外部 HTTPS 网站。"
  else
    print_fail "V2Ray 容器无法访问外部 HTTPS 网站。"
  fi
  
  echo ""
fi

# --- V2Ray 服务检查 ---
if [ -n "$V2RAY_RUNNING" ]; then
  echo "--- V2Ray 服务检查 ---"
  
  # 测试 V2Ray HTTP 端口是否响应（不需要路径，V2Ray 接受任何路径）
  V2RAY_TEST=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 http://127.0.0.1:$V2RAY_PORT/ 2>/dev/null || echo "000")
  if [ "$V2RAY_TEST" != "000" ]; then
    print_success "V2Ray 端口 $V2RAY_PORT 响应正常 (HTTP $V2RAY_TEST)。"
  else
    print_fail "V2Ray 端口 $V2RAY_PORT 无响应。"
    print_info "检查 V2Ray 日志:"
    docker logs avalon-v2ray --tail=10 2>&1 | grep -i "error\|fail\|fatal" | head -n 3
  fi
  
  echo ""
fi

# --- Caddy 服务检查 ---
if [ -n "$CADDY_RUNNING" ]; then
  echo "--- Caddy 服务检查 ---"
  
  # 检查 Caddy 是否有严重错误（排除 UDP buffer 和证书相关的 info）
  CADDY_ERRORS=$(docker logs avalon-caddy --tail=50 2>&1 | grep -E '"level":"error"' | tail -n 3)
  if [ -z "$CADDY_ERRORS" ]; then
    print_success "Caddy 无严重错误。"
  else
    print_fail "Caddy 发现错误:"
    echo "$CADDY_ERRORS" | while read line; do
      echo "  $line"
    done
  fi
  
  # 检查 UDP buffer 警告（仅提示）
  UDP_BUFFER_WARN=$(docker logs avalon-caddy --tail=50 2>&1 | grep "receive buffer size" | tail -n 1)
  if [ -n "$UDP_BUFFER_WARN" ]; then
    print_info "UDP buffer 提示（不影响 HTTPS，仅影响 HTTP/3 性能）"
  fi
  
  # 测试 Caddy HTTP 服务
  CADDY_ROOT=$(curl -s -o /dev/null -w "%{http_code}" --max-time 3 http://127.0.0.1:80 2>/dev/null || echo "000")
  if [ "$CADDY_ROOT" = "200" ] || [ "$CADDY_ROOT" = "404" ] || [ "$CADDY_ROOT" = "308" ]; then
    print_success "Caddy HTTP 服务正常 (HTTP $CADDY_ROOT)。"
    if [ "$CADDY_ROOT" = "308" ]; then
      print_info "  → HTTP 308: 自动重定向到 HTTPS（正常）"
    fi
  else
    print_fail "Caddy HTTP 服务异常 (HTTP $CADDY_ROOT)。"
    print_info "检查日志: docker logs avalon-caddy"
  fi
  
  echo ""
fi

# --- 端到端测试 ---
echo "--- 端到端链路测试 ---"

# Phase 2: 从 Caddyfile 提取第一个用户的秘密路径
FIRST_SECRET_PATH=$(grep -oP 'handle /\K[a-zA-Z0-9]+' Caddyfile 2>/dev/null | head -n 1)

if [ -z "$FIRST_SECRET_PATH" ]; then
  print_fail "无法从 Caddyfile 读取秘密路径"
  print_info "Caddyfile 可能未正确生成，请运行 'make config'"
  FAIL_COUNT=$((FAIL_COUNT + 1))
else
  print_info "测试 WebSocket 升级: /$FIRST_SECRET_PATH"
  
  CURL_OUTPUT=$(curl -k -v --http1.1 \
    -H "Connection: Upgrade" \
    -H "Upgrade: websocket" \
    -H "Sec-WebSocket-Version: 13" \
    -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
    -H "Host: $DOMAIN" \
    --max-time 5 \
    "https://127.0.0.1:443/$FIRST_SECRET_PATH" 2>&1)

if echo "$CURL_OUTPUT" | grep -q "HTTP.*101"; then
  print_success "WebSocket 升级成功 (HTTP 101)！Caddy → V2Ray 链路正常。"
elif echo "$CURL_OUTPUT" | grep -q "HTTP.*200"; then
  print_success "Caddy 正常响应 (HTTP 200)。"
elif echo "$CURL_OUTPUT" | grep -q "HTTP.*404"; then
  print_fail "路径错误 (HTTP 404)。秘密路径可能不匹配。"
elif echo "$CURL_OUTPUT" | grep -q "SSL.*internal error"; then
  # 本地回环 TLS 测试失败是正常的，进行深度诊断确认实际状态
  print_info "本地 TLS 测试: 内部错误（回环测试限制）"
  
  # 深度诊断：直接测试 V2Ray
  print_info "深度诊断: 测试 V2Ray 服务..."
  INTERNAL_TEST=$(curl -s -o /dev/null -w "%{http_code}" --max-time 2 \
    -H "Upgrade: websocket" \
    -H "Connection: Upgrade" \
    http://127.0.0.1:$V2RAY_PORT/$FIRST_SECRET_PATH 2>/dev/null || echo "000")
  
  if [ "$INTERNAL_TEST" = "400" ] || [ "$INTERNAL_TEST" = "404" ]; then
    print_success "V2Ray 服务正常 (HTTP $INTERNAL_TEST)。"
    print_info "  → 本地 TLS 错误可忽略，这是回环测试的已知限制"
    print_info "  → 实际客户端连接不受影响"
    # 不增加 FAIL_COUNT，因为这是正常的
  else
    print_fail "V2Ray 服务异常 (HTTP $INTERNAL_TEST)。"
    print_info "  → 检查 V2Ray 日志: docker logs avalon-v2ray"
  fi
  
elif echo "$CURL_OUTPUT" | grep -q "Connection refused"; then
  print_fail "连接被拒绝。Caddy 可能未启动或端口未开放。"
else
  print_fail "本地测试未通过。"
  ERROR_LINE=$(echo "$CURL_OUTPUT" | grep -E "curl:|error:" | head -n 1)
  if [ -n "$ERROR_LINE" ]; then
    print_info "错误: $ERROR_LINE"
  fi
fi
fi  # 结束 FIRST_SECRET_PATH 检查

echo ""

# --- 客户端连接信息 ---
echo ""
echo "=============================================="
echo "            📱 客户端连接信息"
echo "=============================================="

# 从数据库读取用户信息
if [ -f data/avalon.db ] && command -v python3 &> /dev/null; then
  USER_INFO=$(python3 -c "
import sqlite3
conn = sqlite3.connect('data/avalon.db')
users = conn.execute('SELECT uuid, email FROM users WHERE enabled=1').fetchall()
for uuid, email in users:
    print(f'{email}|{uuid}')
conn.close()
" 2>/dev/null)

  if [ -n "$USER_INFO" ]; then
    echo ""
    while IFS='|' read -r email uuid; do
      echo -e "${GREEN}📧 用户:${NC} $email"
      echo -e "${GREEN}🆔 UUID:${NC} $uuid"
      # Phase 2: 从数据库读取每个用户的秘密路径
      user_path=$(python3 -c "
import sys
sys.path.insert(0, 'app')
from database import Database
db = Database('data/avalon.db')
user = db.get_user_by_uuid('$uuid')
print(user['secret_path'] if user else '')
" 2>/dev/null)
      
      if [ -n "$user_path" ]; then
        echo -e "${GREEN}🔗 连接:${NC} vless://${uuid}@${DOMAIN}:443?type=ws&security=tls&path=%2F${user_path}&host=${DOMAIN}&sni=${DOMAIN}#${email}"
      fi
      echo ""
    done <<< "$USER_INFO"
  fi
fi

# --- 总结 ---
echo "=============================================="
echo "            📊 验证完成"
echo "=============================================="
echo -e "${CYAN}【IPv6-only 环境特殊配置】${NC}"
echo -e "  ${GREEN}✓${NC} Prefer IPv6 (优先使用 IPv6): ${YELLOW}必须开启${NC}"
echo -e "    → 服务器为 IPv6-only 环境，客户端必须优先使用 IPv6"
echo -e "    → 配置路径: 设置 → 网络 → Prefer IPv6 / IPv6 优先"
echo ""
echo -e "${CYAN}【说明】${NC}"
echo -e "  • 此设置${RED}无法通过 URL 传递${NC}，必须在客户端手动配置"
echo -e "  • 不同客户端的选项名称可能不同:"
echo -e "    - V2Box: Prefer IPv6"
echo -e "    - v2rayNG: 优先使用 IPv6"
echo -e "    - Clash: ipv6: true"
echo ""
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo -e "${GREEN}✅ 所有检查通过！${NC}"
else
  echo -e "${YELLOW}⚠️  发现 ${FAIL_COUNT} 个问题（本地 TLS 测试可忽略）${NC}"
fi
echo ""
echo -e "${BLUE}💡 测试建议:${NC}"
if [ -n "$FIRST_SECRET_PATH" ]; then
  echo "   从外网测试: curl -I https://$DOMAIN/$FIRST_SECRET_PATH"
fi
echo "   查看日志: docker compose logs"
echo "=============================================="

exit $FAIL_COUNT
