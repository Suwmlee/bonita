# 构建前端
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ .
RUN npm run build:icons
RUN npm run build

# 构建 Bonita
FROM python:3.12-slim-bullseye AS backend-build

ENV TZ=Asia/Shanghai
ENV MAX_CONCURRENCY=5
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

WORKDIR /app/backend

# 只复制依赖文件，利用缓存层
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# 从前端构建阶段复制静态文件
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# 安装精简版nginx
RUN apt-get update && \
    apt-get install -y --no-install-recommends nginx curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# 复制nginx配置和启动脚本
COPY nginx.conf /etc/nginx/nginx.conf
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 12346

# 启动 Nginx、FastAPI 和 Celery
CMD ["/app/start.sh"]
