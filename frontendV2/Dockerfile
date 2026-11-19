# Production image for the V2 SPA. Nginx serves the built assets and proxies
# /platform to backendV1 so the browser only talks to one origin.
FROM node:24-alpine AS build

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY . .

ARG VITE_SSO_ENABLED=false
ARG VITE_PUBLIC_CHATBOT_SLUG=""
ENV VITE_SSO_ENABLED=$VITE_SSO_ENABLED
ENV VITE_PUBLIC_CHATBOT_SLUG=$VITE_PUBLIC_CHATBOT_SLUG

RUN npm run build

FROM nginx:1.29-alpine

COPY deploy/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html

EXPOSE 80
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD wget -qO- http://127.0.0.1/healthz || exit 1
