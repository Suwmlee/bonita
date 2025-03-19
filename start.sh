#!/bin/bash

# 启动nginx
nginx

# 启动FastAPI，确保数据库初始化完成
echo "启动FastAPI服务..."
uvicorn bonita.main:app --host 0.0.0.0 --port 8000 &
UVICORN_PID=$!

# 等待FastAPI启动完成
echo "等待FastAPI服务启动和数据库初始化..."
until $(curl -X GET --output /dev/null --silent --fail http://localhost:8000/api/v1/status/health); do
  printf "."
  sleep 2
done
echo "FastAPI服务已启动，数据库初始化完成"

# 启动Celery
echo "启动Celery worker..."
celery -A bonita.worker.celery worker --pool threads --concurrency $MAX_CONCURRENCY --events --loglevel DEBUG
