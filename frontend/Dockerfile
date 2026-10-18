# syntax=docker/dockerfile:1
# Build with Node 22 LTS, serve the static bundle with unprivileged nginx,
# which also reverse-proxies /api and /ws to the backend (same origin).
FROM node:22-alpine AS build
WORKDIR /app
COPY package.json package-lock.json ./
# Optional extra CA for TLS-inspecting proxies (see backend/Dockerfile).
RUN --mount=type=secret,id=extra_ca \
    if [ -s /run/secrets/extra_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/extra_ca; fi; \
    npm ci --no-audit --no-fund
COPY . .
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine AS runtime
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=5 CMD wget -qO- http://127.0.0.1:8080/ >/dev/null || exit 1
