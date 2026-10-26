#!/usr/bin/env bash
set -euo pipefail

# Run on the MacBook after `npm run build` and a successful commit.
# Pushes docs/.vuepress/dist to the Mac mini release root and switches `current`.
# The Mac mini must never run the build.

if [ $# -lt 1 ]; then
  echo "usage: $0 <slug>" >&2
  exit 1
fi

SLUG="$1"
REMOTE="${DEPLOY_REMOTE:-codinglog-deploy}"
RELEASES="${DEPLOY_RELEASES:-/Users/mac/coding-log-web-releases}"
HASH="$(git rev-parse --short HEAD)"
DATE="$(date +%Y-%m-%d)"
REL="${DATE}-${SLUG}-${HASH}"

if [ ! -d docs/.vuepress/dist ]; then
  echo "missing docs/.vuepress/dist; run npm run build on this MacBook first" >&2
  exit 1
fi

if ssh "$REMOTE" "test -e '$RELEASES/$REL'"; then
  REL="${REL}-$(date +%H%M%S)"
fi

echo "Deploying $REL from $HASH ..."
ssh "$REMOTE" "mkdir -p '$RELEASES/$REL/dist'"
rsync -az --delete docs/.vuepress/dist/ "$REMOTE:$RELEASES/$REL/dist/"
ssh "$REMOTE" "chmod -R a+rX '$RELEASES/$REL'; chmod 755 '$RELEASES/$REL' '$RELEASES/$REL/dist'; cd '$RELEASES' && ln -s '$REL' .current.tmp && mv -h .current.tmp current && readlink current"
echo "Release $REL is current."
