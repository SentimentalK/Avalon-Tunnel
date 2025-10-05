# 🚀 Avalon Tunnel

**安全、健壮、极致易用的代理解决方案**

Avalon Tunnel 是一个基于 V2Ray (VLESS + WebSocket + TLS) 的智能代理系统，采用 Caddy 自动管理 TLS 证书，并提供完整的全链路自动化诊断功能。

## ✨ 核心特性

### 🎯 简易为先
- **一键部署**: 仅需配置域名，运行 `docker compose up` 即可完成所有设置
- **零配置烦恼**: 秘密路径、用户 UUID 等敏感参数全部自动生成
- **自动 TLS**: Caddy 自动申请和续期 Let's Encrypt 证书

### 🧠 智能配置
- **数据库驱动**: 使用 SQLite 作为配置的"单一数据源"
- **配置持久化**: 所有用户数据持久化存储，容器重启不丢失
- **自动生成链接**: 自动生成 VLESS 客户端连接链接

### 🔍 部署即诊断
- **全链路检测**: 从 DNS 解析到服务通信的完整检查
- **启动前验证**: 只有通过所有诊断，核心服务才会启动
- **实时反馈**: 清晰的诊断输出，问题一目了然

### 🔐 安全可靠
- **伪装网站**: 伪装成普通 HTTPS 网站
- **安全头设置**: 完整的 HTTP 安全头配置
- **审计日志**: 记录所有配置变更历史

## 📂 项目架构

```
Avalon-Tunnel/
├── 📂 app/                    # 核心 Python 管理应用
│   ├── database/             # 数据库模块 (SQLite)
│   │   ├── database.py       # 数据访问层
│   │   └── schema.sql        # 数据库架构
│   ├── services/             # 业务逻辑层
│   │   └── config_service.py # 配置生成服务
│   ├── diagnostics/          # 诊断模块
│   │   └── diagnostic_service.py
│   ├── main.py               # 主入口 - 流程编排
│   └── requirements.txt      # Python 依赖
│
├── 📂 data/                   # 持久化数据目录
│   └── avalon.db             # SQLite 数据库 (自动创建)
│
├── 📂 scripts/                # 系统脚本
│   ├── diagnose.sh           # 全链路诊断脚本
│   └── setup-firewall.sh     # 防火墙配置脚本
│
├── 📂 public/                 # Caddy 伪装网站
│   └── index.html
│
├── 🐳 Dockerfile              # Manager 服务镜像
├── 🐳 docker-compose.yml      # 服务编排
├── 📄 Caddyfile              # Caddy 配置 (自动生成)
├── 📄 config.json            # V2Ray 配置 (自动生成)
├── 📄 .env                    # 环境配置 (需要创建)
└── 📄 env.example             # 配置模板
```

## 🚀 快速开始

### 前置要求

- **服务器**: 一台有公网 IP 的 Linux 服务器 (Ubuntu/Debian 推荐)
- **域名**: 一个已经解析到服务器 IP 的域名
- **Docker**: Docker 20.10+ 和 Docker Compose V2
- **端口**: 开放 80 和 443 端口

### 第一步：准备服务器

#### 1.1 安装 Docker

```bash
# Ubuntu/Debian
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
```

#### 1.2 配置防火墙

```bash
# 如果使用 UFW
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable

# ⚠️ 重要：还需要在云服务商控制台配置安全组
# 允许入站规则：TCP 80, 443
```

### 第二步：克隆项目

```bash
git clone https://github.com/your-repo/Avalon-Tunnel.git
cd Avalon-Tunnel
```

### 第三步：配置域名

```bash
# 复制配置文件模板
cp env.example .env

# 编辑配置文件
nano .env
```

**修改 `.env` 文件中的 `DOMAIN` 为你的真实域名：**

```bash
DOMAIN=your-domain.com  # 改成你的域名，如: example.com
```

> **注意**: 
> - 不要包含 `https://` 前缀
> - 确保域名已经正确解析到服务器 IP
> - `SECRET_PATH` 留空，系统会自动生成

### 第四步：启动服务

```bash
# 构建并启动所有服务
sudo docker compose up --build

# 如果需要后台运行
sudo docker compose up --build -d
```

### 启动流程说明

当你运行 `docker compose up` 时，系统会自动执行以下步骤：

1. **前置检查**: 验证 `.env` 文件和域名配置
2. **系统初始化**: 首次部署时自动创建数据库、生成秘密路径和默认用户
3. **配置生成**: 根据数据库内容生成 V2Ray 和 Caddy 配置文件
4. **全链路诊断**: 检查域名解析、防火墙、网络连接等所有环节
5. **启动服务**: 诊断通过后自动启动 V2Ray 和 Caddy

如果诊断失败，服务**不会启动**，你需要根据错误提示修复问题后重新运行。

## 📱 获取客户端连接信息

部署成功后，在日志输出中会显示客户端连接链接：

```bash
# 查看完整日志
sudo docker compose logs manager

# 你会看到类似这样的输出：
🔗 客户端连接链接:
----------------------------------------------------------------------

📧 default@avalon-tunnel.com
🆔 550e8400-e29b-41d4-a716-446655440000
🔗 vless://550e8400-e29b-41d4-a716-446655440000@your-domain.com:443?...
```

### 使用方法

1. **复制** 完整的 `vless://` 开头的链接
2. 打开客户端 (V2RayN / V2RayNG / Shadowrocket / Quantumult X 等)
3. 点击 **从剪贴板导入** 或 **扫描二维码**
4. 连接并测试

### 支持的客户端

- **Windows**: V2RayN, Clash Verge
- **macOS**: V2RayX, Clash X Pro
- **iOS**: Shadowrocket, Quantumult X
- **Android**: V2RayNG, Clash for Android
- **Linux**: Qv2ray, V2RayA

## 🔧 常用命令

```bash
# 查看服务状态
sudo docker compose ps

# 查看日志
sudo docker compose logs -f

# 重启服务
sudo docker compose restart

# 停止服务
sudo docker compose down

# 完全重新部署
sudo docker compose down
sudo docker compose up --build --force-recreate
```

## 🩺 诊断工具

### 手动运行诊断

如果服务已经运行，你也可以手动运行诊断脚本：

```bash
sudo ./scripts/diagnose.sh
```

诊断脚本会检查：

- ✅ 域名解析是否正确
- ✅ 服务器公网 IP 是否匹配
- ✅ 防火墙配置 (UFW 和云服务商)
- ✅ Docker 容器运行状态
- ✅ 容器 DNS 解析能力
- ✅ 端到端 WebSocket 连接

### 常见问题排查

#### 问题 1: 域名解析失败

```bash
# 检查域名是否解析到正确的 IP
dig +short your-domain.com

# 应该返回你的服务器公网 IP
```

**解决方案**: 在域名提供商处添加 A 记录，等待 DNS 生效 (可能需要几分钟)

#### 问题 2: 无法连接 443 端口

**可能原因**:
- 云服务商安全组未开放 443 端口
- UFW 防火墙未开放 443 端口

**解决方案**:
```bash
# 检查 UFW
sudo ufw status

# 开放端口
sudo ufw allow 443/tcp

# 然后检查云服务商控制台的安全组配置
```

#### 问题 3: 容器 DNS 解析失败

这通常发生在某些云服务商 (如 Oracle Cloud) 上。

**解决方案**: 已经在 `docker-compose.yml` 中配置了公共 DNS (8.8.8.8)，应该不会出现此问题。

## 🔄 管理用户

### 当前阶段 (手动管理)

用户信息存储在 `data/avalon.db` SQLite 数据库中。

#### 查看数据库

```bash
# 安装 sqlite3
sudo apt install sqlite3

# 打开数据库
sqlite3 data/avalon.db

# 查看所有用户
SELECT * FROM users;

# 退出
.quit
```

#### 添加新用户

```python
# 进入 Python 容器
sudo docker exec -it avalon-manager bash

# 运行 Python
python3

# 添加用户
from app.database import Database
db = Database("/app/config/data/avalon.db")

# 创建新用户 (UUID 自动生成)
user = db.create_user(email="newuser@example.com", notes="新用户")
print(f"UUID: {user['uuid']}")

# 重新生成配置并重启服务
exit()
sudo docker compose restart
```

### 未来阶段 (API 管理)

第二阶段将提供 Web API 和管理界面，可以通过 Web 界面轻松管理用户。

## 🏗️ 架构说明

### 工作流程

```
用户运行 docker compose up
    ↓
启动 Manager 服务 (容器化 Python 应用)
    ↓
阶段 1: 检查前置条件 (.env 文件、域名配置)
    ↓
阶段 2: 系统初始化 (首次部署)
    - 创建 SQLite 数据库
    - 生成随机秘密路径
    - 创建默认用户
    ↓
阶段 3: 配置生成
    - 从数据库读取用户信息
    - 生成 config.json (V2Ray)
    - 生成 Caddyfile (Caddy)
    ↓
阶段 4: 全链路诊断
    - 调用 diagnose.sh 脚本
    - 检查网络、DNS、防火墙、容器
    ↓
诊断通过 (exit 0) ──────→ Manager 退出
    ↓                           ↓
Docker Compose 监听到        启动 V2Ray 容器
service_completed_successfully  ↓
    ↓                         启动 Caddy 容器
    ↓                           ↓
所有服务就绪，开始提供代理服务 🎉
```

### 服务职责

- **Manager**: 一次性运行的"大脑"，负责初始化和诊断
- **V2Ray**: 持续运行的核心代理服务
- **Caddy**: 持续运行的反向代理和 TLS 管理

### 数据持久化

- `data/avalon.db`: 用户信息和系统配置
- `caddy_data` volume: TLS 证书
- `caddy_config` volume: Caddy 配置缓存

即使删除容器，这些数据也会保留。

## 🔮 未来规划

### 第二阶段：API 管理后台

- [ ] Flask API 服务
- [ ] RESTful API 端点 (用户增删改查)
- [ ] 实时配置热重载
- [ ] Web 管理界面
- [ ] 流量统计和监控

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## ⚠️ 免责声明

本项目仅供学习和研究使用，请遵守当地法律法规。

---

**Made with ❤️ by Avalon Tunnel Team**

如有问题，请提交 Issue 或查看[诊断指南](scripts/diagnose.sh)。
