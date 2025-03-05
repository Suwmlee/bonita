
## Bonita backend

### 部署

```sh

# 安装依赖
pip install -r requirements.txt

# 启动
uvicorn bonita.main:app --host 0.0.0.0 --port 8000  --reload

# 启动 worker
celery --app bonita.worker.celery worker

# 注册的任务列表
celery --app bonita.worker.celery inspect registered
```

#### alembic迁移

```
alembic init bonita/alembic

alembic revision --autogenerate -m "update"

alembic upgrade head

alembic downgrade -1
```

#### VSCode

```sh
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "FastAPI",
      "type": "debugpy",
      "request": "launch",
      "module": "uvicorn",
      "args": ["app.main:app", "--host=0.0.0.0", "--reload"],
      "jinja": true
    },
    {
      "name": "Celery",
      "type": "debugpy",
      "request": "launch",
      "module": "celery",
      "console": "integratedTerminal",
      "args": [
        "--app",
        "bonita.worker.celery",
        "worker",
        "--loglevel",
        "DEBUG",
        "-P",
        "eventlet",
        "--concurrency",
        "5"
      ]
    }
  ],
  "compounds": [
    {
      "name": "Celery and FastAPI",
      "configurations": ["Celery", "FastAPI"]
    }
  ]
}
```