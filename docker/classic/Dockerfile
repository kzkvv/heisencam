# syntax=docker/dockerfile:1
ARG FRIGATE_BASE=ghcr.io/blakeblackshear/frigate:0.18.3
FROM --platform=$BUILDPLATFORM node:24-bookworm-slim AS web-build
ENV NODE_OPTIONS=--max-old-space-size=4096
WORKDIR /work
COPY web/package.json web/package-lock.json ./
COPY web/patches/ patches/
RUN npm ci --no-audit --no-fund
COPY web/ ./
RUN export VITE_GIT_COMMIT_HASH="$(find public/locales -type f -print0 | sort -z | xargs -0 sha256sum | sha256sum | cut -c1-12)" \
    && npm run build \
    && mv dist/BASE_PATH/monacoeditorwork/* dist/assets/ \
    && rm -rf dist/BASE_PATH

FROM ${FRIGATE_BASE}
WORKDIR /opt/frigate
COPY frigate/ frigate/
COPY tools/quality_replay.py tools/
COPY docker/main/rootfs/usr/local/nginx/conf/nginx.conf /usr/local/nginx/conf/nginx.conf
RUN rm -rf web
ENV PYTHONPATH=/opt/frigate
COPY --from=web-build /work/dist/ web/
