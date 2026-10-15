# ==============================================================================
# QNU.AI Platform — Frontend Production Dockerfile (React 19 + Vite + Nginx)
# ==============================================================================

# Stage 1: Build React Application
FROM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402 AS builder

WORKDIR /app

# Copy dependency manifests
COPY package.json package-lock.json ./

# Install dependencies cleanly
RUN npm ci

# Public OIDC configuration only. Never pass passwords or API keys as build args.
ARG VITE_SSO_AUTHORITY=https://sso.qnu.edu.vn
ARG VITE_SSO_CLIENT_ID=qnu-ai-platform
ARG VITE_SSO_REDIRECT_URI=/signin-oidc
ARG VITE_SSO_POST_LOGOUT_REDIRECT_URI=/sign-in
ARG VITE_SSO_SCOPE="openid profile email roles offline_access ai.api"

# Copy source code and configurations
COPY . ./

# Build production bundle
RUN npm run build

# Stage 2: Serve with lightweight Nginx Alpine
FROM nginx:stable-alpine@sha256:0985e772fb9f729e6fa0980da05fca5d9c468e870eed43071545afa9d2e27d94

# Clean out default static assets
RUN rm -rf /usr/share/nginx/html/*

# Copy built distribution from builder stage
COPY --from=builder /app/dist /usr/share/nginx/html

# Copy custom Nginx configuration
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Healthcheck probe
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
  CMD wget --no-verbose --tries=1 --spider http://127.0.0.1/ || exit 1

CMD ["nginx", "-g", "daemon off;"]
