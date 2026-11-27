#!/usr/bin/env bash
set -euo pipefail

image="${1:?Pass the image under test}"
revision="${2:?Pass its source revision}"
test "$(docker image inspect "$image" --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}')" = "$revision"
docker run --rm --network none --entrypoint python3 "$image" -m unittest \
  frigate.test.test_detection_evidence frigate.test.test_debug_replay \
  frigate.test.test_video frigate.test.test_performance \
  frigate.test.test_review_fixes frigate.test.http_api.test_http_event \
  frigate.test.http_api.test_http_media
docker run --rm --network none --entrypoint python3 -v "$PWD/tools:/opt/frigate/tools:ro" "$image" \
  -m unittest discover -s /opt/frigate/tools -p test_performance_smoke.py
docker run --rm --network none --entrypoint python3 \
  -v "$PWD/generate_api_auth_spec.py:/opt/frigate/generate_api_auth_spec.py:ro" \
  -v "$PWD/docs/static:/opt/frigate/docs/static:ro" "$image" /opt/frigate/generate_api_auth_spec.py --check

export HEISENCAM_IMAGE="$image" HEISENCAM_PORT="${HEISENCAM_PORT:-8974}"
export COMPOSE_PROJECT_NAME="${COMPOSE_PROJECT_NAME:-candidate-sample}"
compose=(docker compose -f examples/demo/compose.yml)
cleanup() {
  "${compose[@]}" logs --tail 60 || true
  "${compose[@]}" down -v
}
trap cleanup EXIT
started=$(date +%s)
"${compose[@]}" up -d --wait --wait-timeout 120
python3 tools/check_demo_capture.py --base-url "http://127.0.0.1:$HEISENCAM_PORT" --started "$started"
