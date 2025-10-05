# Avalon Tunnel - Manager 服务 Dockerfile
# 构建智能配置与诊断系统

FROM python:3.11-slim

LABEL maintainer="Avalon Tunnel Team"
LABEL description="Avalon Tunnel Manager - 智能配置与诊断系统"

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    bash \
    curl \
    dnsutils \
    netcat-traditional \
    iproute2 \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制 Python 应用代码
COPY app/ /app/

# 安装 Python 依赖（当前只有标准库，为未来准备）
RUN pip install --no-cache-dir -r requirements.txt

# 设置 Python 环境
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# 设置默认命令
CMD ["python", "main.py", "--base-dir", "/app/config"]

