
## Bonita

[![GitHub Workflow Status](https://img.shields.io/github/actions/workflow/status/suwmlee/bonita/docker-publish.yml?branch=master)](https://github.com/suwmlee/bonita/actions) [![Docker Pulls](https://img.shields.io/docker/pulls/suwmlee/bonita)](https://hub.docker.com/r/suwmlee/bonita)

安心享受影片

特性:
- 自动检测影视文件，自动入库
- 管理视频元数据
- 自定义刮削
- 整理、迁移视频文件
- 管理观影记录、喜爱的影片
- 同步emby

待做:
- 同步各个媒体服务记录，无痛迁移
- 影片推荐
- 推送服务
- 关联下载器


### 部署

#### Docker

```sh
# 拉取镜像
docker pull suwmlee/bonita:latest

# 指定登录账户和密码
FIRST_SUPERUSER_EMAIL
FIRST_SUPERUSER_PASSWORD

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

参考各端 `README`

如果期望使用Redis，手动修改 `/backend/bonita/core/config` 内路径
```sh
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```
