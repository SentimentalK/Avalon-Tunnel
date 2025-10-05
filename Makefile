.PHONY: help setup check-pre check-post check config deploy start stop restart logs clean status

help:
	@echo "🚀 Avalon Tunnel - 可用命令"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  make deploy       - 完整部署（防火墙+配置生成+启动+验证）"
	@echo "  make config       - 仅生成配置文件"
	@echo "  make setup        - 仅配置防火墙"
	@echo "  make check-pre    - 仅运行环境预检查"
	@echo "  make check-post   - 仅运行服务验证"
	@echo "  make start        - 快速启动（跳过所有检查）"
	@echo "  make stop         - 停止服务"
	@echo "  make logs         - 查看日志"
	@echo "  make status       - 查看状态"
	@echo "  make clean        - 完全清理"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# 检查 .env 文件
check-env:
	@if [ ! -f .env ]; then \
		echo "❌ 错误: .env 文件不存在"; \
		echo "   请先创建: cp env.example .env"; \
		exit 1; \
	fi
	@if ! grep -q "^DOMAIN=" .env || grep -q "DOMAIN=your-domain.com" .env; then \
		echo "❌ 错误: 未配置 DOMAIN"; \
		echo "   请编辑 .env 文件"; \
		exit 1; \
	fi
	@echo "✅ .env 配置检查通过"

# 配置防火墙
setup: check-env
	@echo "🔥 配置防火墙..."
	@sudo bash scripts/setup-firewall.sh
	@echo ""

# 生成配置文件（Python Manager）
config: check-env
	@echo "⚙️  生成配置文件..."
	@docker compose run --rm --build manager
	@echo "✅ 配置已生成"
	@echo ""

# 环境预检查（在生成配置后）
check-pre: config
	@sudo -E PATH=$$PATH bash scripts/diagnose-pre.sh

# 服务验证
check-post:
	@sudo -E PATH=$$PATH bash scripts/diagnose-post.sh

# 完整部署
deploy: setup check-pre
	@echo "🚀 启动服务..."
	@docker compose up -d v2ray caddy
	@sleep 3
	@echo ""
	@make check-post
	@echo ""
	@echo "✅ 部署完成！"
	@docker compose ps

# 快速启动
start:
	@docker compose up -d v2ray caddy
	@docker compose ps

# 停止
stop:
	@docker compose stop v2ray caddy

# 重启
restart: stop start

# 日志
logs:
	@docker compose logs -f v2ray caddy

# 状态
status:
	@docker compose ps

# 清理
clean:
	@docker compose down
