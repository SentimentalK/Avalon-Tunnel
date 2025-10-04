# Avalon Tunnel - 高度伪装的代理服务

一个基于 V2Ray + Caddy 的现代化、安全且高度伪装的代理服务解决方案。

## 🚀 特性

- **高度伪装**: 服务器表现为标准 HTTPS 网站，完美隐藏代理特征
- **自动 TLS**: 使用 Caddy 自动申请和续期 Let's Encrypt 证书
- **多层安全**: 防火墙 + 应用层认证 + 网络隔离
- **容器化部署**: 基于 Docker 的一键部署
- **IPv6 支持**: 原生支持 IPv6 网络环境

## 🏗️ 架构

```
Internet → Caddy (443/HTTPS) → V2Ray (10000/WebSocket) → 目标网络
```

- **Caddy**: 反向代理 + TLS 终端 + 伪装网站
- **V2Ray**: VLESS + WebSocket + TLS 代理核心
- **防火墙**: 仅开放必要端口 (22, 80, 443)

## 📋 系统要求

- Ubuntu 20.04+ (或其他 Linux 发行版)
- Docker & Docker Compose
- 一个有效域名
- 服务器公网 IP (支持 IPv6)

## 🛠️ 快速部署

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd Avalon-Tunnel
```

### 2. 配置环境

```bash
# 复制环境配置文件
cp env.example .env

# 编辑配置文件
nano .env
```

**重要配置项：**
- `DOMAIN`: 您的域名
- `SECRET_PATH`: 自定义的秘密路径
- `USER1_UUID`, `USER2_UUID`: 用户认证 UUID

### 3. 生成 UUID

```bash
# 生成新的用户 UUID
./scripts/generate-uuid.sh
```

### 4. 配置防火墙

```bash
# 自动配置 UFW 防火墙
./scripts/setup-firewall.sh
```

### 5. 部署服务

```bash
# 一键部署
./scripts/deploy.sh
```

## 🔧 配置说明

### 环境变量 (.env)

```bash
# 域名配置 (必须)
DOMAIN=your-domain.com

# 秘密路径 (建议使用随机字符串)
SECRET_PATH=avalon-secret-path

# 用户 UUID (使用脚本生成)
USER1_UUID=550e8400-e29b-41d4-a716-446655440000
USER2_UUID=6ba7b810-9dad-11d1-80b4-00c04fd430c8
```

### V2Ray 配置

主要配置在 `config.json` 中：

- **协议**: VLESS
- **传输**: WebSocket
- **端口**: 10000 (内部)
- **认证**: UUID 密钥

### Caddy 配置

主要配置在 `Caddyfile` 中：

- **TLS**: 自动 Let's Encrypt
- **伪装**: 静态网站
- **代理**: 秘密路径转发

## 📱 客户端配置

### V2Ray 客户端配置

```json
{
  "address": "your-domain.com",
  "port": 443,
  "id": "your-uuid",
  "security": "auto",
  "network": "ws",
  "wsSettings": {
    "path": "/your-secret-path"
  }
}
```

### 支持的客户端

- V2RayN (Windows)
- V2RayX (macOS)
- V2Box (Android)
- Shadowrocket (iOS)

## 🛡️ 安全特性

### 网络层安全

- **防火墙**: 仅开放必要端口
- **端口隐藏**: V2Ray 端口不对外暴露
- **IPv6 支持**: 原生 IPv6 网络支持

### 应用层安全

- **UUID 认证**: 高强度用户认证
- **TLS 加密**: 端到端加密传输
- **路径隐藏**: 自定义秘密路径

### 伪装特性

- **网站伪装**: 标准 HTTPS 网站外观
- **流量混淆**: 与正常网站流量无异
- **协议隐藏**: 完全隐藏代理特征

## 📊 管理命令

```bash
# 查看服务状态
docker-compose ps

# 查看服务日志
docker-compose logs

# 重启服务
docker-compose restart

# 停止服务
docker-compose down

# 更新服务
docker-compose pull
docker-compose up -d
```

## 🔍 故障排除

### 常见问题

1. **证书申请失败**
   - 检查域名 DNS 解析
   - 确保 80 端口可访问
   - 检查防火墙设置

2. **代理连接失败**
   - 验证 UUID 配置
   - 检查秘密路径设置
   - 确认客户端配置

3. **服务启动失败**
   - 查看容器日志: `docker-compose logs`
   - 检查配置文件语法
   - 验证端口占用情况

### 日志查看

```bash
# 查看所有服务日志
docker-compose logs

# 查看特定服务日志
docker-compose logs caddy
docker-compose logs v2ray

# 实时查看日志
docker-compose logs -f
```

## 🔄 更新升级

```bash
# 拉取最新镜像
docker-compose pull

# 重启服务
docker-compose up -d

# 清理旧镜像
docker image prune
```

## 📈 性能优化

### 系统优化

```bash
# 增加文件描述符限制
echo "* soft nofile 65535" >> /etc/security/limits.conf
echo "* hard nofile 65535" >> /etc/security/limits.conf

# 优化网络参数
echo "net.core.rmem_max = 16777216" >> /etc/sysctl.conf
echo "net.core.wmem_max = 16777216" >> /etc/sysctl.conf
sysctl -p
```

### 容器优化

- 使用 `restart: unless-stopped` 确保服务自启动
- 配置适当的资源限制
- 定期清理日志文件

## 🆘 技术支持

如遇到问题，请检查：

1. 系统日志: `journalctl -u docker`
2. 容器日志: `docker-compose logs`
3. 网络连接: `netstat -tlnp`
4. 防火墙状态: `ufw status`

## 📄 许可证

本项目采用 MIT 许可证。详见 [LICENSE](LICENSE) 文件。

## ⚠️ 免责声明

本项目仅供学习和研究使用。使用者需遵守当地法律法规，作者不承担任何法律责任。

---

**Avalon Tunnel** - 让网络连接更安全、更隐蔽
