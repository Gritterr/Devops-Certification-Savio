#!/usr/bin/env bash
# Objective 1: download the company website files.
#
# Fetches the case-study repository at a pinned commit and copies only the
# website folder ("Case-study app") into ./website, which the Dockerfile copies
# into the image. Pinning the commit means every build gets the same files.
set -euo pipefail

REPO_URL="https://github.com/edurekacontent/dockerContent"
COMMIT="77063e25ffa4872ee2b182d6e7b8727ff1174633"

here="$(cd "$(dirname "$0")" && pwd)"
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT

git -C "$tmp" init -q
git -C "$tmp" fetch -q --depth 1 "$REPO_URL" "$COMMIT"
git -C "$tmp" checkout -q FETCH_HEAD

rm -rf "$here/website"
cp -R "$tmp/Case-study app" "$here/website"
echo "Website files copied to $here/website ($(find "$here/website" -type f | wc -l | tr -d ' ') files)"
