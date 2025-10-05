# Avalon Tunnel - Manager 服务 Dockerfile
# 轻量级配置生成服务

FROM python:3.11-alpine

LABEL maintainer="Avalon Tunnel Team"
LABEL description="Avalon Tunnel Manager - 配置生成服务"

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

