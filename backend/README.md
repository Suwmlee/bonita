
## Bonita backend

### 部署

```sh
poetry install

# 进入虚拟环境
poetry shell

# 启动
uvicorn app.main:app app.main:app --host 0.0.0.0 --port 8000  --reload
```

#### alembic迁移

```
alembic init app/alembic

alembic revision --autogenerate -m "update"

alembic upgrade head

alembic downgrade -1
```
