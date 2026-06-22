#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_PATH="$ROOT_DIR/dist/MediaSeg.app"
FFMPEG_VERSION="${MEDIASEG_FFMPEG_VERSION:-7.1.5}"
FFMPEG_WORK_ROOT="${MEDIASEG_FFMPEG_WORK_ROOT:-$ROOT_DIR/.cache/ffmpeg-lgpl}"
FFMPEG_SOURCE_DIR="${MEDIASEG_FFMPEG_SOURCE_DIR:-$FFMPEG_WORK_ROOT/install/ffmpeg-$FFMPEG_VERSION}"
FFMPEG_SOURCE_ARCHIVE="$FFMPEG_WORK_ROOT/artifacts/ffmpeg-$FFMPEG_VERSION-mediaseg-source.tar.xz"
FFMPEG_BUILD_NOTES="$FFMPEG_WORK_ROOT/artifacts/ffmpeg-$FFMPEG_VERSION-build-configuration.txt"

cd "$ROOT_DIR"
source .venv/bin/activate
mkdir -p assets/build
git rev-parse --short HEAD > assets/build/build_sha.txt
pyinstaller --clean -y MediaSeg.spec
./tools/build_lgpl_ffmpeg.sh
python3 tools/bundle_ffmpeg.py "$APP_PATH/Contents/Resources/ffmpeg" "$FFMPEG_SOURCE_DIR"
cp "$FFMPEG_SOURCE_ARCHIVE" "$ROOT_DIR/dist/MediaSeg-ffmpeg-$FFMPEG_VERSION-source.tar.xz"
cp "$FFMPEG_BUILD_NOTES" "$ROOT_DIR/dist/MediaSeg-ffmpeg-$FFMPEG_VERSION-build-configuration.txt"
codesign --force --deep --sign - "$APP_PATH"
