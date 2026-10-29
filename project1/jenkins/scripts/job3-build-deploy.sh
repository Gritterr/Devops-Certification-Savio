#!/bin/bash
# Job 3: build the PHP website image from the Dockerfile in the git repo and
# deploy it as a container on the test server. Runs on the agent "test-server"
# in a checkout of the repo's master branch.
set -eu
IMAGE=projcert-php
CONTAINER=php-website
PORT=8081            # 80 and 8080 are already used on this test server

docker build -t "$IMAGE:$BUILD_NUMBER" -t "$IMAGE:latest" .

# Replace the previous deployment
docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
docker run -d --name "$CONTAINER" --restart unless-stopped -p "$PORT:80" "$IMAGE:$BUILD_NUMBER"

# Smoke test: the home page must load and show the site's title
for i in $(seq 1 20); do curl -fs -o /dev/null "http://localhost:$PORT/" && break; sleep 1; done
curl -fs "http://localhost:$PORT/" | grep -q "Simple PHP Website"

# Lets the failure path (Post-build Task) be demonstrated on demand
if [ "${SIMULATE_FAILURE:-false}" = "true" ]; then
  echo "SIMULATE_FAILURE=true: failing on purpose to test the cleanup step"
  exit 1
fi

echo "Deployed build $BUILD_NUMBER: http://10.79.140.67:$PORT/"
