
## Bonita


### 部署

#### Docker

```sh
docker build -t suwmlee/bonita:latest -f Dockerfile  .

# 使用外部 Redis,不使用则去掉 CELERY_BROKER_URL、CELERY_RESULT_BACKEND
docker run -d \
    --name bonita \
    -p 12346:80 \
    -e CELERY_BROKER_URL="redis://host.docker.internal:6379/0" \
    -e CELERY_RESULT_BACKEND="redis://host.docker.internal:6379/0" \
    -v <path/to/media>:/media \
    -V <path/to/data>:"/app/backend/data" \
    suwmlee/bonita:latest
```

#### 源码部署

如果期望使用Redis，手动修改 `/backend/bonita/core/config` 内路径
`CELERY_BROKER_URL` `CELERY_RESULT_BACKEND`
redis://localhost:6379/0
