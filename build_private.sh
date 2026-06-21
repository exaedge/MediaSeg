#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="$ROOT_DIR/dist/MediaSeg.app"
DMG_PATH="$ROOT_DIR/dist/MediaSeg.dmg"

cleanup() {
    if [[ -n "${STAGE_DIR:-}" && -d "${STAGE_DIR:-}" ]]; then
        rm -rf "$STAGE_DIR"
    fi
}

trap cleanup EXIT

cd "$ROOT_DIR"
source .venv/bin/activate
mkdir -p assets/build
git rev-parse --short HEAD > assets/build/build_sha.txt
pyinstaller --clean -y MediaSeg.spec
codesign --force --deep --sign - "$APP_PATH"

STAGE_DIR="$(mktemp -d /private/tmp/mediaseg-dmg.XXXXXX)"
cp -R "$APP_PATH" "$STAGE_DIR/"
ln -s /Applications "$STAGE_DIR/Applications"
hdiutil create -ov -format UDZO -volname MediaSeg -srcfolder "$STAGE_DIR" "$DMG_PATH"
