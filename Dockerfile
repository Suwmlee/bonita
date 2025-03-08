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

WORKDIR /app/backend

COPY backend/ /app/backend/
RUN pip install -r /app/backend/requirements.txt --no-cache-dir

# 从前端构建阶段复制静态文件
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

RUN apt-get update && apt-get install -y nginx
COPY nginx.conf /etc/nginx/nginx.conf

EXPOSE 12346

# 启动 Nginx、FastAPI 和 Celery
CMD ["sh", "-c", "nginx && uvicorn bonita.main:app --host 0.0.0.0 --port 8000 & celery -A bonita.worker.celery worker --pool threads --concurrency $MAX_CONCURRENCY --events --loglevel DEBUG"]
