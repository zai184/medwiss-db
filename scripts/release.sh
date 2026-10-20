#!/usr/bin/env bash
# Generic release script: bump version, version the CHANGELOG, tag and push.
# Install as scripts/release.sh in a repo. Usage: ./scripts/release.sh X.Y.Z
#
# Manifest detection (first match wins):
#   1. pyproject.toml        (root)         — `version = "..."`
#   2. package.json          (root)         — `"version": "..."`
#   3. manifest.json         (root)         — `"version": "..."`
#   4. apps/api/pyproject.toml + apps/web/package.json  — SPA+API pair, bumped together
#   5. apps/web/package.json             — web-only monorepo
#   6. flake.nix / requirements.txt / none  — no manifest; CHANGELOG + tag only
# If no `## [Unreleased]` section exists in CHANGELOG.md, a dated release entry
# is prepended. A missing CHANGELOG.md is created.
set -euo pipefail

VERSION="${1:-}"
if [[ ! "$VERSION" =~ ^[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
    echo "Usage: $0 X.Y.Z (semver)" >&2
    exit 1
fi
TAG="v$VERSION"
ROOT="$(git rev-parse --show-toplevel)"
cd "$ROOT"
TODAY="$(date +%Y-%m-%d)"

# 1. Clean tree required — a release is exactly the tagged commit.
if [[ -n "$(git status --porcelain)" ]]; then
    echo "ERROR: working tree not clean. Commit or stash first." >&2
    exit 1
fi

bump_toml() { sed -i "s/^version = \".*\"/version = \"$VERSION\"/" "$1"; }
bump_json() { sed -i "0,/\"version\": \"[^\"]*\"/s//\"version\": \"$VERSION\"/" "$1"; }

MANIFESTS=()
if [[ -f pyproject.toml ]] && grep -q '^version' pyproject.toml; then
    MANIFESTS=(pyproject.toml)
elif [[ -f package.json ]] && grep -q '"version"' package.json; then
    MANIFESTS=(package.json)
elif [[ -f manifest.json ]] && grep -q '"version"' manifest.json; then
    MANIFESTS=(manifest.json)
elif [[ -f apps/api/pyproject.toml && -f apps/web/package.json ]]; then
    MANIFESTS=(apps/api/pyproject.toml apps/web/package.json)
elif [[ -f apps/web/package.json ]] && grep -q '"version"' apps/web/package.json; then
    MANIFESTS=(apps/web/package.json)
else
    echo "no manifest found — CHANGELOG + tag only"
fi

for m in "${MANIFESTS[@]}"; do
    case "$m" in
        *.toml) bump_toml "$m" ;;
        *.json) bump_json "$m" ;;
    esac
    echo "bumped $m -> $VERSION"
done

# 2. CHANGELOG: version all [Unreleased] sections; create file/entry if needed.
if [[ ! -f CHANGELOG.md ]]; then
    printf '# Changelog\n\nAll notable changes are documented here.\n\n## [%s] - %s\n### Added\n- Release %s.\n\n' \
        "$VERSION" "$TODAY" "$VERSION" > CHANGELOG.md
elif grep -q '^## \[Unreleased\]' CHANGELOG.md; then
    sed -i "s/^## \[Unreleased\]/## [$VERSION]/" CHANGELOG.md
else
    sed -i "1a\\
\\
## [$VERSION] - $TODAY\\
### Added\\
- Release $VERSION." CHANGELOG.md
fi
if grep -q '^## \[Unreleased\]' CHANGELOG.md; then
    echo "ERROR: Unreleased sections remain in CHANGELOG.md" >&2
    exit 1
fi

git add -A
git commit -m "release: $TAG"

# 3. Annotated tag + push with tags.
git tag -a "$TAG" -m "Release $TAG — see CHANGELOG.md"
git push origin HEAD --follow-tags 2>/dev/null || git push backup HEAD --follow-tags

echo "Released $TAG"
