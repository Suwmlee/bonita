# 构建前端
FROM node:20 AS frontend-build
WORKDIR /app/frontend
COPY frontend/ .
RUN npm install
RUN npm run build:icons
RUN npm run build

# 构建 Bonita
FROM python:3.12

ENV TZ=Asia/Shanghai
ENV MAX_CONCURRENCY=5

# update TZ
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && \
    echo $TZ > /etc/timezone

WORKDIR /app/backend

COPY backend/ /app/backend/
RUN pip install -r /app/backend/requirements.txt --no-cache-dir

# 从前端构建阶段复制静态文件
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

RUN apt-get update && apt-get install -y nginx curl
COPY nginx.conf /etc/nginx/nginx.conf

# 复制启动脚本
COPY start.sh /app/start.sh
RUN chmod +x /app/start.sh

EXPOSE 12346

# 启动 Nginx、FastAPI 和 Celery
CMD ["/app/start.sh"]
