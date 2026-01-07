# frontend/Dockerfile
# 阶段 1: 构建
FROM node:20-alpine AS builder
WORKDIR /app

# 配置 npm 使用国内镜像源（可选，如果网络好可以注释掉）
RUN npm config set registry https://registry.npmmirror.com

# 复制依赖文件
COPY package.json package-lock.json* ./

# 安装依赖（使用缓存和离线优先）
RUN npm install --prefer-offline --no-audit

# 复制源码
COPY . .

# 设置构建时的环境变量 (重要：如果你的 Next.js 代码里用了 ENV，需要在构建时传入，或者在运行时通过 next.config.js 暴露)
# 注意：这里先给一个占位符，实际部署时通常在浏览器端直接请求后端 URL
ARG NEXT_PUBLIC_API_BASE_URL
ENV NEXT_PUBLIC_API_BASE_URL=${NEXT_PUBLIC_API_BASE_URL}

# 构建 Next.js 应用（使用缓存）
RUN npm run build

# 阶段 2: 运行
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# 创建非 root 用户增加安全性
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# 复制构建产物
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]

