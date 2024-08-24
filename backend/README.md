
## Bonita backend

### 部署

```sh

# python 版本需要 3.10 以上
# 使用 virtulenv 新建环境
python3 -m pip install venv
python3 -m venv .venv

# 安装依赖
pip install -r requirements.txt

# 启动
uvicorn app.main:app app.main:app --host 0.0.0.0 --port 12380  --reload
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
