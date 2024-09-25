
## Bonita frontend

### 安装

```sh
# 使用 nvm 管理 node
nvm ls

# 安装并使用
nvm install 20
nvm use 20

# 安装依赖
npm install

npm run dev
```

### 更新 .env

```sh
# dev
VITE_API_URL="http://localhost:8000"
```

### icon

https://boxicons.com/

### 更新 client API
```sh
node modify-openapi-operationids.js

npm run generate-client
```
