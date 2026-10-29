#!/bin/bash
# Task 4: if Job 3 fails, delete the running container on the test server.
# Run by the Post-build Task plugin when Job 3's log shows a failed build step.
echo "Job 3 failed: removing the php-website container from the test server"
docker rm -f php-website || true
