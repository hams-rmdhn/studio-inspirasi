#!/usr/bin/env bash
# SPDX-License-Identifier: AGPL-3.0-or-later
# Pulls the newest Clovercut upstream into this Studio Inspirasi fork and
# rebuilds, keeping the two things that make this tree ours intact:
#
#   1. the Studio Inspirasi brand (scripts/branding/apply-brand.py), and
#   2. the macOS Monterey 12 compatibility layer
#      (scripts/macos/libc++_monterey_shim.cpp + build-macos-local.sh).
#
# Remotes are expected as:
#   origin    hams-rmdhn/studio-inspirasi   (this fork)
#   upstream  tulcoturo/clovercut           (what we track)
#
#   scripts/macos/sync-upstream.sh [--no-build]
#
# On a merge conflict the script stops: resolve the listed files, prefer
# upstream's version everywhere it conflicts (the brand overlay puts ours
# back), `git merge --continue` or `git add -A && git commit`, then run
# the script again with --no-build to re-apply and finish.

set -euo pipefail

ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
cd "$ROOT"

NO_BUILD=0
[ "${1:-}" = "--no-build" ] && NO_BUILD=1

echo "==> [1/4] Fetching upstream (tulcoturo/clovercut)"
git fetch upstream

BRANCH="$(git branch --show-current)"
echo "==> [2/4] Merging upstream/main into $BRANCH"
if ! git merge --no-edit upstream/main; then
  cat >&2 <<'MSG'

Merge conflicts. Resolve them - taking upstream's side is always safe,
because the brand overlay re-applies our identity - then:

  git add -A && git merge --continue
  scripts/macos/sync-upstream.sh --no-build

MSG
  exit 1
fi

echo "==> [3/4] Re-applying the Studio Inspirasi brand overlay"
python3 scripts/branding/apply-brand.py

if [ "$NO_BUILD" -eq 0 ]; then
  echo "==> [4/4] Rebuilding the macOS 12 bundle and DMG"
  scripts/macos/build-macos-local.sh
else
  echo "==> [4/4] Skipped the build (--no-build)"
fi

echo "==> Sync complete. Review 'git log upstream/main..HEAD' before pushing."
