#!/bin/bash

# Avalon Tunnel - 一键部署脚本
# 此脚本将自动部署整个代理服务

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 打印带颜色的消息
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

# 检查必要的命令
check_requirements() {
    print_info "检查系统要求..."
    
    if ! command -v docker >/dev/null 2>&1; then
        print_error "Docker 未安装，请先安装 Docker"
        exit 1
    fi
    
    if ! command -v docker-compose >/dev/null 2>&1; then
        print_error "Docker Compose 未安装，请先安装 Docker Compose"
        exit 1
    fi
    
    print_success "系统要求检查通过"
}

# 检查配置文件
check_config() {
    print_info "检查配置文件..."
    
    if [ ! -f "docker-compose.yml" ]; then
        print_error "docker-compose.yml 文件不存在"
        exit 1
    fi
    
    if [ ! -f "Caddyfile" ]; then
        print_error "Caddyfile 文件不存在"
        exit 1
    fi
    
    if [ ! -f "config.json" ]; then
        print_error "config.json 文件不存在"
        exit 1
    fi
    
    if [ ! -f "public/index.html" ]; then
        print_error "public/index.html 文件不存在"
        exit 1
    fi
    
    print_success "配置文件检查通过"
}

# 检查环境变量
check_env() {
    print_info "检查环境配置..."
    
    if [ ! -f ".env" ]; then
        print_warning ".env 文件不存在，使用默认配置"
        if [ -f "env.example" ]; then
            print_info "请复制 env.example 为 .env 并填入您的配置"
            print_info "cp env.example .env"
            print_info "然后编辑 .env 文件填入您的域名等信息"
        fi
    else
        print_success "环境配置文件存在"
    fi
}

# 停止现有服务
stop_services() {
    print_info "停止现有服务..."
    docker-compose down 2>/dev/null || true
    print_success "现有服务已停止"
}

# 启动服务
start_services() {
    print_info "启动 Avalon Tunnel 服务..."
    
    # 创建必要的目录
    mkdir -p public
    mkdir -p logs
    
    # 启动服务
    docker-compose up -d
    
    print_success "服务启动完成"
}

# 检查服务状态
check_services() {
    print_info "检查服务状态..."
    
    # 等待服务启动
    sleep 10
    
    # 检查容器状态
    if docker-compose ps | grep -q "Up"; then
        print_success "服务运行正常"
    else
        print_error "服务启动失败，请检查日志"
        docker-compose logs
        exit 1
    fi
}

# 显示服务信息
show_info() {
    print_info "服务部署完成！"
    echo ""
    echo "🌐 服务信息："
    echo "   - 伪装网站: https://你的域名"
    echo "   - 代理路径: https://你的域名/你的秘密路径"
    echo "   - V2Ray 端口: 10000 (内部)"
    echo ""
    echo "📊 管理命令："
    echo "   - 查看状态: docker-compose ps"
    echo "   - 查看日志: docker-compose logs"
    echo "   - 停止服务: docker-compose down"
    echo "   - 重启服务: docker-compose restart"
    echo ""
    echo "🔧 客户端配置："
    echo "   - 地址: 你的域名"
    echo "   - 端口: 443"
    echo "   - 用户ID: 你的UUID"
    echo "   - 传输协议: WebSocket"
    echo "   - 路径: 你的秘密路径"
    echo "   - TLS: 开启"
    echo ""
    print_warning "请确保已配置防火墙，只开放 22, 80, 443 端口"
}

# 主函数
main() {
    echo "🚀 Avalon Tunnel 部署脚本"
    echo "================================"
    echo ""
    
    check_requirements
    check_config
    check_env
    stop_services
    start_services
    check_services
    show_info
    
    echo ""
    print_success "部署完成！"
}

# 运行主函数
main "$@"
