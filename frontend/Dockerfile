# syntax=docker/dockerfile:1

# Base images are pinned by version and digest so a rebuild months later uses the same bytes.
ARG NODE_IMAGE=node:24.19.0-alpine@sha256:d32cdf619f63fe0471182d08996dd516c6275bb5fd31ae06e55a570bd9e1ad43
# NGINX's official non-root image: runs as uid 101 and listens on an unprivileged port.
ARG NGINX_IMAGE=nginxinc/nginx-unprivileged:1.31.6-alpine@sha256:6a23acdfca2b9cfbcec61419e3f1426bcbedb91362f2f19306a8567423bb4612

# ---- build: type-check and bundle the app ------------------------------------------------------
FROM ${NODE_IMAGE} AS build
WORKDIR /app
# Dependency files first: code changes do not invalidate the install layer.
COPY package.json package-lock.json ./
# Exactly the lockfile. Install scripts are skipped, as locally (the only one, msw's, just
# copies a browser worker that the build does not use).
RUN npm ci --ignore-scripts
COPY . .
# The browser calls the API directly, so its origin is compiled into the bundle (Vite inlines
# VITE_* at build time). Changing the API origin means rebuilding this image.
ARG VITE_API_BASE_URL=http://localhost:8000
ENV VITE_API_BASE_URL=${VITE_API_BASE_URL}
RUN npm run build

# ---- runtime: static files served by nginx; no Node at runtime ---------------------------------
FROM ${NGINX_IMAGE} AS runtime
ARG VITE_API_BASE_URL=http://localhost:8000
# Read by the nginx templates at container start: the port (Railway sets PORT) and the API origin
# allowed by the Content-Security-Policy (the same origin the bundle was built for).
ENV PORT=8080 \
    API_ORIGIN=${VITE_API_BASE_URL}
COPY nginx/default.conf.template nginx/security-headers.inc.template /etc/nginx/templates/
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --start-period=5s --retries=3 \
  CMD wget -q -O /dev/null "http://127.0.0.1:${PORT}/" || exit 1
