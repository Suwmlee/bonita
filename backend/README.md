
## Bonita backend

### 部署

```sh
poetry install

# 进入虚拟环境
poetry shell

# 启动
uvicorn app.main:app app.main:app --host 0.0.0.0 --port 12380  --reload
```

#### alembic迁移

```
alembic init app/alembic

alembic revision --autogenerate -m "update"

alembic upgrade head

alembic downgrade -1
```


#### 注册为服务
```sh
[Unit]
Description=Bonita application
After=network.target

[Service]
User=root
Group=www-data
WorkingDirectory=/var/apps/backend
ExecStart=/var/apps/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

```sh
sudo systemctl daemon-reload
sudo systemctl start Bonita.service
sudo systemctl enable Bonita.service
```
