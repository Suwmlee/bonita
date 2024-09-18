
## Bonita backend

### 部署

```sh
poetry install

# 进入虚拟环境
poetry shell

# 启动
uvicorn app.main:app app.main:app --host 0.0.0.0 --port 8000  --reload

# 启动 worker
celery --app app.main.celery worker

# 注册的任务列表
celery --app app.main.celery inspect registered
```

#### alembic迁移

```
alembic init app/alembic

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
        "app.worker.celery",
        "worker",
        "--loglevel",
        "DEBUG",
        "-P",
        "solo"
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