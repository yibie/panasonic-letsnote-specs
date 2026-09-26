#!/bin/sh
# Publish docs/ (built by build_site.py) to https://letsnote-specs.github.io/
# via the letsnote-specs/letsnote-specs.github.io repository.
set -e
ROOT=$(cd "$(dirname "$0")/.." && pwd)
SITE_REPO=letsnote-specs/letsnote-specs.github.io
CHECKOUT="$ROOT/.cache/site-repo"

[ -d "$CHECKOUT/.git" ] || gh repo clone "$SITE_REPO" "$CHECKOUT"
git -C "$CHECKOUT" pull -q --ff-only 2>/dev/null || true
rsync -a --delete --exclude .git "$ROOT/docs/" "$CHECKOUT/"
git -C "$CHECKOUT" add -A
if git -C "$CHECKOUT" diff --cached --quiet; then
  echo "site unchanged"
else
  git -C "$CHECKOUT" commit -q -m "Update site from panasonic-letsnote-specs@$(git -C "$ROOT" rev-parse --short HEAD)"
  git -C "$CHECKOUT" push -q -u origin HEAD:main
  echo "site pushed"
fi
