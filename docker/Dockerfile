# 构建前端
FROM node:20-slim AS frontend-build
WORKDIR /app/frontend
COPY ../frontend/package*.json ./
RUN npm install
COPY ../frontend/ .
RUN npm run build:icons
RUN npm run build

# 构建 Bonita with s6-overlay
FROM python:3.12-slim-bullseye AS backend-build

# s6-overlay 版本
ARG S6_OVERLAY_VERSION=3.1.6.2

ENV TZ=Asia/Shanghai
ENV MAX_CONCURRENCY=5
# 添加用户配置环境变量
ENV PUID=0
ENV PGID=0
# s6-overlay 环境变量
ENV S6_BEHAVIOUR_IF_STAGE2_FAILS=2
ENV S6_CMD_WAIT_FOR_SERVICES_MAXTIME=0

RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime &&
    echo $TZ >/etc/timezone

# 安装 s6-overlay
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-noarch.tar.xz /tmp
ADD https://github.com/just-containers/s6-overlay/releases/download/v${S6_OVERLAY_VERSION}/s6-overlay-x86_64.tar.xz /tmp
RUN tar -C / -Jxpf /tmp/s6-overlay-noarch.tar.xz &&
    tar -C / -Jxpf /tmp/s6-overlay-x86_64.tar.xz &&
    rm -rf /tmp/*

WORKDIR /app/backend

# 只复制依赖文件，利用缓存层
COPY ../backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY ../backend/ .

# 从前端构建阶段复制静态文件
COPY --from=frontend-build /app/frontend/dist /app/frontend/dist

# 安装精简版nginx
RUN apt-get update &&
    apt-get install -y --no-install-recommends nginx curl &&
    apt-get clean &&
    rm -rf /var/lib/apt/lists/*

# 创建应用用户和相关目录
RUN groupadd -g 1000 bonita &&
    useradd -u 1000 -g bonita -d /app -s /bin/bash bonita &&
    mkdir -p /var/log/nginx /var/lib/nginx /var/run &&
    mkdir -p /var/lib/nginx/body /var/lib/nginx/fastcgi /var/lib/nginx/proxy /var/lib/nginx/scgi /var/lib/nginx/uwsgi &&
    chown -R bonita:bonita /app /var/log/nginx /var/lib/nginx /var/run

# 复制nginx配置
COPY nginx.conf /etc/nginx/nginx.conf

# 复制 s6-overlay 配置文件
COPY --chmod=755 cont-init.d /etc/cont-init.d/
COPY --chmod=755 s6-rc.d /etc/s6-overlay/s6-rc.d/

EXPOSE 12346

ENTRYPOINT ["/init"]
