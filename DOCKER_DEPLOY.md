# Docker 部署指南

## 前置要求

- Docker 20.10+
- Docker Compose 2.0+ (或使用 `docker compose` 命令)

## 快速部署

### 1. 本地测试部署

在项目根目录执行：

```bash
docker-compose up -d --build
```

或者使用新版本的命令：

```bash
docker compose up -d --build
```

### 2. 查看日志

```bash
# 查看所有服务日志
docker-compose logs -f

# 查看特定服务日志
docker-compose logs -f backend
docker-compose logs -f frontend
```

### 3. 停止服务

```bash
docker-compose down
```

## 生产环境部署

### 1. 修改环境变量

编辑 `docker-compose.yml`，将 `NEXT_PUBLIC_API_BASE_URL` 修改为你的服务器公网地址：

```yaml
frontend:
  environment:
    - NEXT_PUBLIC_API_BASE_URL=http://<你的服务器IP>:8001
```

**重要**：这个地址必须是浏览器能够访问到的地址。如果你的服务器有域名，建议使用域名。

### 2. 使用 Nginx 反向代理（推荐）

为了更好的生产环境部署，建议使用 Nginx 作为反向代理：

```nginx
# /etc/nginx/sites-available/mcp-workflow
server {
    listen 80;
    server_name your-domain.com;

    # 前端
    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    # 后端 API
    location /api {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket 支持
    location /ws {
        proxy_pass http://localhost:8001;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

然后修改 `docker-compose.yml` 中的 `NEXT_PUBLIC_API_BASE_URL` 为：

```yaml
- NEXT_PUBLIC_API_BASE_URL=http://your-domain.com/api
```

### 3. 数据持久化

项目已经配置了以下目录的持久化挂载：

- `./backend/logs` - 日志文件
- `./backend/scripts` - 生成的脚本
- `./backend/storage` - 存储文件
- `./backend/app.db` - SQLite 数据库

确保这些目录在宿主机上有适当的权限：

```bash
mkdir -p backend/logs backend/scripts backend/storage
chmod -R 755 backend/logs backend/scripts backend/storage
```

### 4. 更新部署

当代码更新后，重新构建并启动：

```bash
docker-compose up -d --build
```

## 故障排查

### 1. 端口冲突

如果 3000 或 8001 端口被占用，修改 `docker-compose.yml` 中的端口映射：

```yaml
ports:
  - "3001:3000"  # 将前端映射到 3001
  - "8002:8001"  # 将后端映射到 8002
```

### 2. 权限问题

如果遇到文件写入权限问题：

```bash
sudo chown -R $USER:$USER backend/logs backend/scripts backend/storage
```

### 3. 查看容器状态

```bash
docker-compose ps
```

### 4. 进入容器调试

```bash
# 进入后端容器
docker-compose exec backend bash

# 进入前端容器
docker-compose exec frontend sh
```

## 安全建议

1. **生产环境不要使用 SQLite**：考虑使用 PostgreSQL 或 MySQL
2. **使用 HTTPS**：配置 SSL 证书（Let's Encrypt）
3. **限制端口暴露**：使用防火墙只开放必要端口
4. **定期更新镜像**：保持基础镜像和依赖的更新
5. **环境变量管理**：使用 Docker secrets 或外部密钥管理服务

