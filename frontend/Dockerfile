ARG BUILD_VERSION=dev
ARG BUILD_COMMIT=unknown

# Multi-stage build for AI Resume Frontend
# Builds React SPA and serves with OpenResty (Alpine package)

# =============================================================================
# Stage 1: Build React application
# =============================================================================
# node 26.4.0-trixie-slim, pinned 2026-06-29
FROM node:26.8.1-trixie-slim@sha256:c0753125a3789977aefe869cbebccf70e3cfd7ea84ca48547458f02e4f1d7146 AS builder

WORKDIR /app

# Update system packages to fix CVE-2025-14831 and CVE-2025-9820 (GnuTLS vulnerabilities)
RUN apt-get update && apt-get upgrade -y && apt-get clean

RUN npm install -g npm@11.12.1

# Copy package files first for better layer caching
COPY package.json package-lock.json ./

# Install dependencies
RUN npm ci --prefer-offline --no-audit

# Copy source code
COPY index.html vite.config.ts tsconfig.json tsconfig.app.json tsconfig.node.json ./
COPY public/ ./public/
COPY src/ ./src/

# Build production bundle
RUN npm run build

ARG BUILD_VERSION
ARG BUILD_COMMIT
RUN printf '{"version":"%s","commit":"%s"}\n' "${BUILD_VERSION}" "${BUILD_COMMIT}" > /app/VERSION

# =============================================================================
# Stage 2: Production OpenResty server (Alpine package)
# =============================================================================
# alpine 3.23.4, pinned 2026-05-31
FROM alpine:3.24.1@sha256:28bd5fe8b56d1bd048e5babf5b10710ebe0bae67db86916198a6eec434943f8b

# Install OpenResty and lua-resty-http, then create directories
# Note: openresty package creates 'nginx' user and group automatically
# OpenResty bundles lua-resty-dns, lua-resty-core, cjson, and LuaJIT.
# lua-resty-http is installed via opm (not apk) to avoid the Alpine
# nginx 1.28 / openresty nginx 1.27 package conflict.
# DL3018: don't pin apk versions -- Alpine's rolling repo rotates exact
# versions out (a pin breaks the build on the next refresh); the digest-pinned
# base plus `apk upgrade --no-cache` already fix the patch level.
# hadolint ignore=DL3018
RUN apk upgrade --no-cache && \
    apk add --no-cache openresty curl && \
    curl -fsSL -o /usr/lib/nginx/lualib/resty/http.lua \
      https://raw.githubusercontent.com/ledgetech/lua-resty-http/v0.17.2/lib/resty/http.lua && \
    curl -fsSL -o /usr/lib/nginx/lualib/resty/http_connect.lua \
      https://raw.githubusercontent.com/ledgetech/lua-resty-http/v0.17.2/lib/resty/http_connect.lua && \
    curl -fsSL -o /usr/lib/nginx/lualib/resty/http_headers.lua \
      https://raw.githubusercontent.com/ledgetech/lua-resty-http/v0.17.2/lib/resty/http_headers.lua && \
    apk del curl && \
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
COPY --from=builder /app/VERSION /usr/share/nginx/html/VERSION

# Switch to non-root user
USER nginx

# Expose unprivileged port
EXPOSE 8080

STOPSIGNAL SIGTERM
CMD ["nginx", "-c", "/etc/nginx/nginx.conf", "-g", "daemon off;"]
