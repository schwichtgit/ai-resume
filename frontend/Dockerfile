# Multi-stage build for AI Resume Frontend
# Builds React SPA and serves with OpenResty (Alpine package)

# =============================================================================
# Stage 1: Build React application
# =============================================================================
FROM node:24.13.0-bookworm-slim AS builder

WORKDIR /app

RUN npm install -g npm@11.8.0

# Copy package files first for better layer caching
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci --prefer-offline --no-audit

# Copy source code
COPY index.html vite.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY tailwind.config.ts postcss.config.js ./
COPY public/ ./public/
COPY src/ ./src/

# Build production bundle
RUN npm run build

# =============================================================================
# Stage 2: Production OpenResty server (Alpine package)
# =============================================================================
FROM alpine:3.23

# Install OpenResty, lua-resty-dns for dynamic DNS, and create directories
# Note: openresty package creates 'nginx' user and group automatically
# lua-resty-dns brings in all dependencies: lua-resty-core, nginx-mod-http-lua, luajit
RUN apk add --no-cache \
        openresty \
        lua-resty-http \
        lua-resty-dns && \
    mkdir -p /etc/nginx/conf.d /etc/nginx/lua /etc/nginx/html /var/log/nginx /var/run/nginx /usr/share/nginx/html && \
    ln -sf /dev/stdout /var/log/nginx/access.log && \
    ln -sf /dev/stderr /var/log/nginx/error.log && \
    chown -R nginx:nginx /etc/nginx/lua /etc/nginx/html /var/run/nginx /usr/share/nginx/html && \
    find /usr/share/nginx -type d -exec chmod 750 {} + && \
    find /usr/share/nginx -type f -exec chmod 640 {} + && \
    chgrp -R nginx /usr/share/nginx && \
    mkdir -p /var/cache/nginx && \
    chown -R nginx:nginx /var/cache/nginx

# Copy server configuration (uses Lua to read env vars at runtime)
COPY nginx-default.conf /etc/nginx/conf.d/default.conf
COPY nginx.conf /etc/nginx/nginx.conf

# Copy Lua handler script
COPY lua/seo-handler.lua /etc/nginx/lua/seo-handler.lua

# Copy SEO template
COPY seo-template.html /etc/nginx/html/seo-template.html

# Copy built React assets
COPY --from=builder /app/dist /usr/share/nginx/html

# Switch to non-root user
USER nginx

# Expose unprivileged port
EXPOSE 8080

STOPSIGNAL SIGTERM
CMD ["nginx", "-g", "daemon off;"]
