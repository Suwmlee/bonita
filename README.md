
## Bonita


#### Docker

注意:
访问路径： host.docker.internal

```sh
docker build -t suwmlee/bonita:latest -f Dockerfile  .


docker run -d \
    --name bonita \
    -e TZ=Asia/Shanghai \
    -p 12346:80 \
    suwmlee/bonita:latest
```
