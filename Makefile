.PHONY: help setup check-pre check-post check config deploy start stop restart logs clean clean-data status api-start api-stop api-restart api-logs

help:
	@echo "🚀 Avalon Tunnel - 可用命令"
	@echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
	@echo "  核心服务:"
	@echo "    make deploy       - 完整部署（防火墙+配置+启动+验证+API）"
	@echo "    make config       - 仅生成配置文件"
	@echo "    make setup        - 仅配置防火墙"
	@echo "    make start        - 快速启动核心服务（V2Ray + Caddy）"
	@echo "    make stop         - 停止所有服务"
	@echo "    make restart      - 重启核心服务"
	@echo ""
	@echo "  API 管理:"
	@echo "    make api-start    - 启动 API 服务器"
	@echo "    make api-stop     - 停止 API 服务器"
	@echo "    make api-restart  - 重启 API 服务器"
	@echo "    make api-logs     - 查看 API 日志"
	@echo ""
	@echo "  诊断与维护:"
	@echo "    make check-pre    - 环境预检查"
	@echo "    make check-post   - 服务验证"
	@echo "    make logs         - 查看所有日志"
	@echo "    make status       - 查看服务状态"
	@echo "    make clean        - 清理所有容器"
	@echo "    make clean-data   - ⚠️  清理用户数据（危险）"
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
	@echo "🚀 启动核心服务（V2Ray + Caddy）..."
	@docker compose up -d v2ray caddy
	@echo "⏳ 等待服务初始化..."
	@sleep 5
	@echo ""
	@echo "🔍 运行服务验证..."
	@make check-post
	@echo ""
	@echo "🚀 启动 API 服务器..."
	@docker compose --profile api up -d api
	@echo ""
	@echo "✅ 部署完成！"
	@echo "📖 API 文档: http://localhost:8000/docs"
	@docker compose ps

# 快速启动（核心服务）
start:
	@echo "🚀 启动核心服务..."
	@docker compose up -d v2ray caddy
	@docker compose ps

# 停止所有服务
stop:
	@echo "🛑 停止所有服务..."
	@docker compose stop v2ray caddy
	@docker compose --profile api stop api
	@echo "✅ 服务已停止"

# 重启核心服务
restart: stop start

# 日志
logs:
	@docker compose logs -f

# API 管理
api-start:
	@echo "🚀 启动 API 服务器..."
	@docker compose --profile api up -d --build api
	@sleep 2
	@echo ""
	@API_STATUS=$$(docker inspect avalon-api --format='{{.State.Status}}' 2>/dev/null || echo "not found"); \
	if [ "$$API_STATUS" = "running" ]; then \
		echo "✅ API 服务器已启动"; \
		echo "📖 API 文档: https://$$DOMAIN/docs"; \
	else \
		echo "❌ API 启动失败，查看日志: docker logs avalon-api"; \
	fi

api-stop:
	@echo "🛑 停止 API 服务器..."
	@docker compose --profile api stop api
	@echo "✅ API 服务器已停止"

api-restart:
	@echo "🔄 重启 API 服务器..."
	@docker compose --profile api restart api
	@echo "✅ API 服务器已重启"

api-logs:
	@docker compose --profile api logs -f api

# 状态
status:
	@docker compose ps
	@echo ""
	@API_STATUS=$$(docker ps --filter "name=avalon-api" --format "{{.Status}}" 2>/dev/null); \
	if [ -n "$$API_STATUS" ]; then \
		echo "API 服务: $$API_STATUS"; \
	else \
		echo "API 服务: 未启动"; \
	fi

# 清理容器
clean:
	@echo "🧹 停止并清理所有容器..."
	@docker compose --profile api down
	@echo "✅ 容器已清理（数据库保留）"

# 清理用户数据（危险操作）
clean-data:
	@echo "⚠️  警告: 此操作将删除所有用户数据和配置！"
	@echo "按 Ctrl+C 取消，或按 Enter 继续..."
	@read confirm
	@echo "🗑️  删除数据库..."
	@rm -f data/avalon.db
	@echo "🗑️  删除生成的配置文件..."
	@rm -f config.json Caddyfile
	@echo "✅ 用户数据已清理"
	@echo "💡 下次运行 'make config' 将重新初始化并生成新的秘密路径"
