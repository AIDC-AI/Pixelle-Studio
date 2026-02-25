# frontend/Dockerfile
# Stage 1: Build
FROM node:20-alpine AS builder
WORKDIR /app

# Configure npm mirror source (optional, comment out if network is good)
RUN npm config set registry https://registry.npmmirror.com

# Copy dependency files
COPY package.json package-lock.json* ./

# Install dependencies (with cache and offline-first)
RUN npm install --prefer-offline --no-audit

# Copy source code
COPY . .

# Set build-time environment variables (important: if Next.js code uses ENV, pass them at build time or expose via next.config.js at runtime)
# Note: placeholder values here, actual deployment typically has browser directly request backend URL
ARG NEXT_PUBLIC_API_BASE=http://localhost:8001/api
ARG NEXT_PUBLIC_WS_BASE=ws://localhost:8001/ws
ENV NEXT_PUBLIC_API_BASE=${NEXT_PUBLIC_API_BASE}
ENV NEXT_PUBLIC_WS_BASE=${NEXT_PUBLIC_WS_BASE}

# Build Next.js application (with cache)
RUN npm run build

# Stage 2: Run
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production

# Create non-root user for security
RUN addgroup --system --gid 1001 nodejs
RUN adduser --system --uid 1001 nextjs

# Copy build artifacts
COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 3000

ENV PORT=3000
ENV HOSTNAME="0.0.0.0"

CMD ["node", "server.js"]
