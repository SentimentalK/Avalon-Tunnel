#!/bin/bash

# Avalon Tunnel - 配置更新脚本
# 用于更新 V2Ray 用户配置和重启服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_error() {
    echo -e "${RED}❌ $1${NC}"
}

# 检查配置文件是否存在
check_config() {
    if [ ! -f "config.json" ]; then
        print_error "config.json 文件不存在"
        exit 1
    fi
    print_success "配置文件检查通过"
}

# 备份当前配置
backup_config() {
    local backup_file="config.json.backup.$(date +%Y%m%d_%H%M%S)"
    cp config.json "$backup_file"
    print_info "配置已备份到: $backup_file"
}

# 生成新的 UUID
generate_uuid() {
    if command -v uuidgen >/dev/null 2>&1; then
        uuidgen
    elif command -v python3 >/dev/null 2>&1; then
        python3 -c "import uuid; print(uuid.uuid4())"
    else
        print_error "无法生成 UUID，请安装 uuid-runtime 或 python3"
        exit 1
    fi
}

# 添加新用户
add_user() {
    local email="$1"
    local uuid=$(generate_uuid)
    
    print_info "添加新用户: $email"
    print_info "UUID: $uuid"
    
    # 这里可以添加更复杂的 JSON 处理逻辑
    # 目前需要手动编辑 config.json
    print_warning "请手动编辑 config.json 添加新用户："
    echo "  {"
    echo "    \"id\": \"$uuid\","
    echo "    \"level\": 0,"
    echo "    \"email\": \"$email\""
    echo "  }"
}

# 重启服务
restart_services() {
    print_info "重启服务..."
    docker-compose restart v2ray
    print_success "V2Ray 服务已重启"
}

# 显示当前用户
show_users() {
    print_info "当前配置的用户："
    if command -v jq >/dev/null 2>&1; then
        jq -r '.inbounds[0].settings.clients[] | "  - \(.email): \(.id)"' config.json
    else
        print_warning "请安装 jq 以自动解析用户信息"
        print_info "手动查看 config.json 中的 clients 部分"
    fi
}

# 主函数
main() {
    echo "🔧 Avalon Tunnel 配置更新工具"
    echo "================================"
    echo ""
    
    check_config
    
    case "${1:-help}" in
        "add")
            if [ -z "$2" ]; then
                print_error "请提供用户邮箱"
                echo "用法: $0 add user@example.com"
                exit 1
            fi
            backup_config
            add_user "$2"
            ;;
        "restart")
            restart_services
            ;;
        "users")
            show_users
            ;;
        "backup")
            backup_config
            ;;
        *)
            echo "用法: $0 {add|restart|users|backup}"
            echo ""
            echo "命令说明："
            echo "  add <email>    - 添加新用户"
            echo "  restart        - 重启 V2Ray 服务"
            echo "  users          - 显示当前用户"
            echo "  backup         - 备份当前配置"
            echo ""
            echo "示例："
            echo "  $0 add user@example.com"
            echo "  $0 restart"
            echo "  $0 users"
            ;;
    esac
}

main "$@"
