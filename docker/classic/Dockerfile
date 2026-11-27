# syntax=docker/dockerfile:1
ARG FRIGATE_BASE=ghcr.io/blakeblackshear/frigate:0.18.3@sha256:d1a3e0008557bb3f3314d442ecd4ba68e9b16ab7872d64612649f7a6e5156635
FROM --platform=$BUILDPLATFORM node:24-bookworm-slim@sha256:873f586f3794f52281bd039bf02c048a0be08fde619338f9941bad1eb6b34530 AS web-build
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
ARG HEISENCAM_REVISION=development
ARG HEISENCAM_CHANNEL=development
ENV HEISENCAM_REVISION=$HEISENCAM_REVISION HEISENCAM_CHANNEL=$HEISENCAM_CHANNEL
LABEL org.opencontainers.image.title="HeisenCam" \
      org.opencontainers.image.source="https://github.com/kzkvv/heisencam" \
      org.opencontainers.image.revision="${HEISENCAM_REVISION}" \
      org.opencontainers.image.licenses="MIT"
WORKDIR /opt/frigate
COPY LICENSE TRADEMARK.md ./
COPY frigate/ frigate/
COPY tools/quality_replay.py tools/
COPY docker/main/rootfs/usr/local/nginx/conf/nginx.conf /usr/local/nginx/conf/nginx.conf
COPY docker/main/rootfs/usr/local/go2rtc/create_config.py /usr/local/go2rtc/create_config.py
COPY docker/main/rootfs/etc/s6-overlay/s6-rc.d/frigate/run /etc/s6-overlay/s6-rc.d/frigate/run
RUN rm -rf web
ENV PYTHONPATH=/opt/frigate
COPY --from=web-build /work/dist/ web/
HEALTHCHECK --start-period=120s --start-interval=5s --interval=15s --timeout=5s --retries=3 \
    CMD test -f /dev/shm/.frigate-is-stopping || curl --fail --silent http://127.0.0.1:5001/ready
