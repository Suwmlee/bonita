
## Bonita


### 部署

#### Docker

```sh
# 拉取镜像
docker pull suwmlee/bonita:latest

# 默认使用SQLite作为broker
docker run -d \
    --name bonita \
    -e FIRST_SUPERUSER_EMAIL="admin@example.com" \
    -e FIRST_SUPERUSER_PASSWORD="12345678" \
    -p 12346:12346 \
    -v <path/to/media>:/media \
    -V <path/to/data>:/app/backend/data \
    suwmlee/bonita:latest

# 或者使用外部Redis作为broker
docker run -d \
    --name bonita \
    -p 12346:80 \
    -e CELERY_BROKER_URL="redis://host.docker.internal:6379/0" \
    -e CELERY_RESULT_BACKEND="redis://host.docker.internal:6379/0" \
    -v <path/to/media>:/media \
    -V <path/to/data>:/app/backend/data \
    suwmlee/bonita:latest
```

#### 源码部署

如果期望使用Redis，手动修改 `/backend/bonita/core/config` 内路径
`CELERY_BROKER_URL` `CELERY_RESULT_BACKEND`
redis://localhost:6379/0

