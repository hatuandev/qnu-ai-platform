FROM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402 AS builder
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY . ./

# Only public SPA settings may enter the bundle. No API/provider key build args.
ARG VITE_QNU_API_BASE_URL=
ARG VITE_SSO_AUTHORITY=https://sso.qnu.edu.vn
ARG VITE_SSO_CLIENT_ID=qnu-ai-platform
ARG VITE_SSO_REDIRECT_URI=/signin-oidc
ARG VITE_SSO_POST_LOGOUT_REDIRECT_URI=/sign-in
ARG VITE_SSO_SCOPE="openid profile email roles offline_access ai.api"
ARG VITE_DEV_AUTH_ENABLED=false
ENV VITE_QNU_API_BASE_URL=$VITE_QNU_API_BASE_URL \
    VITE_SSO_AUTHORITY=$VITE_SSO_AUTHORITY \
    VITE_SSO_CLIENT_ID=$VITE_SSO_CLIENT_ID \
    VITE_SSO_REDIRECT_URI=$VITE_SSO_REDIRECT_URI \
    VITE_SSO_POST_LOGOUT_REDIRECT_URI=$VITE_SSO_POST_LOGOUT_REDIRECT_URI \
    VITE_SSO_SCOPE=$VITE_SSO_SCOPE \
    VITE_DEV_AUTH_ENABLED=$VITE_DEV_AUTH_ENABLED
RUN npm run build

FROM nginx:stable-alpine@sha256:0985e772fb9f729e6fa0980da05fca5d9c468e870eed43071545afa9d2e27d94
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf
EXPOSE 80
HEALTHCHECK --interval=20s --timeout=5s --start-period=5s --retries=3 \
    CMD wget -q -O /dev/null http://127.0.0.1/health/live || exit 1
CMD ["nginx", "-g", "daemon off;"]
