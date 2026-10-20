# 参与开发

本地需要同时跑三个进程：后端 API、Celery、前端。后端命令在 `backend` 目录执行，前端命令在 `frontend` 目录执行。数据库、缓存和日志默认写在运行目录下的 `data`，所以不要在仓库根目录启动后端。

环境：Python 3.12，Node.js 22，pnpm 11.17（与 `frontend/package.json` 的 `packageManager` 一致）。

## 后端

```sh
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
alembic upgrade head
```

`alembic upgrade head` 会把 SQLite 建到 `backend/data/db.sqlite3`。以后改了模型，在 `backend` 里生成并执行迁移：

```sh
alembic revision --autogenerate -m "update"
alembic upgrade head
```

启动 API：

```sh
uvicorn bonita.main:app --host 0.0.0.0 --port 8000 --reload
```

接口文档在 http://localhost:8000/api/v1/openapi.json 。

转移、刮削、媒体库扫描这些任务不在 API 进程里执行，需要再开一个 Celery worker。`--beat` 会带上定时任务（例如观看记录同步）：

```sh
celery --app bonita.worker.celery worker --pool threads --concurrency 5 --events --loglevel DEBUG --beat
```

确认任务已经注册：

```sh
celery --app bonita.worker.celery inspect registered
```

VS Code 的 FastAPI / Celery 调试配置见 `backend/README.md`。

## 前端

```sh
cd frontend
nvm use 22
corepack enable
pnpm install
```

开发服务器默认是 http://localhost:3000 ，请求发往 `VITE_API_URL`。在 `frontend/.env` 里写：

```sh
VITE_API_URL="http://localhost:8000"
```

然后启动：

```sh
pnpm dev
```

图标来自 [Boxicons](https://boxicons.com/)。新增图标后执行 `pnpm run build:icons`。

## 前端接口

页面调用的是 `frontend/src/client` 里由 [openapi-ts](https://github.com/hey-api/openapi-ts) 生成的客户端，例如 `MetadataService`、`SubtitleService`。不要在 `frontend/src` 里另写一套请求封装。

后端接口有变动时，先保证 API 在 8000 端口运行，再在 `frontend` 重新生成：

```sh
curl -o openapi.json http://localhost:8000/api/v1/openapi.json
pnpm run generate-client
```

`generate-client` 会先用 `modify-openapi-operationids.js` 整理 operationId，再按 `openapi-ts.config.ts` 输出到 `src/client`。把生成结果和后端改动一起提交。`openapi.json` 只是生成时的输入，不必提交。
