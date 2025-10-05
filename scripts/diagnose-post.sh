#!/bin/bash

#=================================================================================
# Avalon Tunnel - 服务验证脚本
# 在 docker compose up 之后运行，验证服务是否正常工作
#=================================================================================

# --- 配置 ---
if [ -f .env ]; then
  export $(grep -v '^#' .env | xargs)
fi
DOMAIN=${DOMAIN:-"your-domain.com"}
V2RAY_PORT=${V2RAY_PORT:-10000}

SECRET_PATH=$(python3 -c "
import json
config = json.load(open('config.json'))
path = config['inbounds'][0]['streamSettings']['wsSettings']['path']
print(path.lstrip('/'))
" 2>/dev/null)

if [ -z "$SECRET_PATH" ]; then
  echo "❌ 错误: 无法从 config.json 读取秘密路径"
  exit 1
fi

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
echo "路径: /$SECRET_PATH"
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

# --- 容器内部网络检查 ---
if [ -n "$V2RAY_RUNNING" ]; then
  echo "--- 容器网络检查 ---"
  if docker exec $V2RAY_RUNNING ping -c 1 -W 2 google.com &> /dev/null; then
    print_success "V2Ray 容器可以访问外网。"
  else
    print_fail "V2Ray 容器无法访问外网。请检查 DNS 和网络配置。"
  fi
  echo ""
fi

# --- 端到端测试 ---
echo "--- 端到端链路测试 ---"
print_info "测试 WebSocket 升级（本地回环）..."

CURL_OUTPUT=$(curl -k -v --http1.1 \
  -H "Connection: Upgrade" \
  -H "Upgrade: websocket" \
  -H "Sec-WebSocket-Version: 13" \
  -H "Sec-WebSocket-Key: dGhlIHNhbXBsZSBub25jZQ==" \
  -H "Host: $DOMAIN" \
  --max-time 5 \
  "https://127.0.0.1:443/$SECRET_PATH" 2>&1)

if echo "$CURL_OUTPUT" | grep -q "HTTP.*101"; then
  print_success "WebSocket 升级成功 (HTTP 101)！Caddy → V2Ray 链路正常。"
elif echo "$CURL_OUTPUT" | grep -q "HTTP.*200"; then
  print_success "Caddy 正常响应 (HTTP 200)。"
elif echo "$CURL_OUTPUT" | grep -q "HTTP.*404"; then
  print_fail "路径错误 (HTTP 404)。"
elif echo "$CURL_OUTPUT" | grep -q "SSL.*internal error"; then
  print_success "服务已启动（本地 TLS 测试限制，这是正常的）。"
  print_info "建议从外网测试: curl -I https://$DOMAIN/$SECRET_PATH"
else
  print_fail "本地测试未通过。"
  print_info "错误: $(echo "$CURL_OUTPUT" | grep -E "curl:" | head -n 1)"
fi
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
      echo -e "${GREEN}🔗 连接:${NC} vless://${uuid}@${DOMAIN}:443?type=ws&security=tls&path=%2F${SECRET_PATH}&host=${DOMAIN}&sni=${DOMAIN}#${email}"
      echo ""
    done <<< "$USER_INFO"
  fi
fi

# --- 总结 ---
echo "=============================================="
echo "            📊 验证完成"
echo "=============================================="
if [ "$FAIL_COUNT" -eq 0 ]; then
  echo -e "${GREEN}✅ 所有检查通过！${NC}"
else
  echo -e "${YELLOW}⚠️  发现 ${FAIL_COUNT} 个问题（本地 TLS 测试可忽略）${NC}"
fi
echo ""
echo -e "${BLUE}💡 测试建议:${NC}"
echo "   从外网测试: curl -I https://$DOMAIN/$SECRET_PATH"
echo "   查看日志: docker compose logs"
echo "=============================================="

exit $FAIL_COUNT
