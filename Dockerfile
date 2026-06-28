# Avalon Tunnel - FastAPI API Server & Decoy Website
FROM python:3.11-slim

WORKDIR /opt/avalon

# 复制依赖文件并安装
COPY app/requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用及伪装网静态资源代码
COPY app/ app/
COPY public/ public/

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV BASE_DIR=/opt/avalon

# 暴露 FastAPI API 端口
EXPOSE 8000

# 启动命令
CMD ["uvicorn", "app.api_server:app", "--host", "0.0.0.0", "--port", "8000"]
