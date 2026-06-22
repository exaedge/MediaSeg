#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
FFMPEG_VERSION="${MEDIASEG_FFMPEG_VERSION:-7.1.5}"
WORK_ROOT="${MEDIASEG_FFMPEG_WORK_ROOT:-$ROOT_DIR/.cache/ffmpeg-lgpl}"
SOURCE_DIR="${MEDIASEG_FFMPEG_SOURCE_DIR:-$WORK_ROOT/install/ffmpeg-$FFMPEG_VERSION}"
DOWNLOAD_DIR="$WORK_ROOT/downloads"
SRC_PARENT="$WORK_ROOT/src"
BUILD_PARENT="$WORK_ROOT/build"
ARTIFACT_DIR="$WORK_ROOT/artifacts"
TARBALL_NAME="ffmpeg-$FFMPEG_VERSION.tar.xz"
SOURCE_URL="https://ffmpeg.org/releases/$TARBALL_NAME"
TARBALL_PATH="$DOWNLOAD_DIR/$TARBALL_NAME"
SRC_DIR="$SRC_PARENT/ffmpeg-$FFMPEG_VERSION"
BUILD_DIR="$BUILD_PARENT/ffmpeg-$FFMPEG_VERSION"
SOURCE_BUNDLE_PATH="$ARTIFACT_DIR/ffmpeg-$FFMPEG_VERSION-mediaseg-source.tar.xz"
BUILD_NOTES_PATH="$ARTIFACT_DIR/ffmpeg-$FFMPEG_VERSION-build-configuration.txt"

CONFIGURE_FLAGS=(
  "--prefix=$SOURCE_DIR"
  "--enable-shared"
  "--disable-static"
  "--disable-autodetect"
  "--disable-network"
  "--enable-pthreads"
  "--enable-version3"
  "--cc=clang"
  "--disable-doc"
  "--disable-debug"
  "--disable-ffplay"
  "--enable-videotoolbox"
  "--enable-audiotoolbox"
  "--enable-neon"
)

if [[ -x "$SOURCE_DIR/bin/ffmpeg" && -f "$SOURCE_BUNDLE_PATH" && -f "$BUILD_NOTES_PATH" ]]; then
  BUILD_CONF="$("$SOURCE_DIR/bin/ffmpeg" -buildconf 2>/dev/null || true)"
  if printf '%s\n' "$BUILD_CONF" | grep -q -- '--enable-gpl\|--enable-nonfree'; then
    echo "Existing FFmpeg build at $SOURCE_DIR is not LGPL-compatible." >&2
    exit 1
  fi
  REBUILD_REQUIRED=0
  for flag in "${CONFIGURE_FLAGS[@]}"; do
    if ! printf '%s\n' "$BUILD_CONF" | grep -q -- "$flag"; then
      REBUILD_REQUIRED=1
      break
    fi
  done
  if [[ "$REBUILD_REQUIRED" -eq 0 ]]; then
    echo "$SOURCE_DIR"
    exit 0
  fi
fi

mkdir -p "$DOWNLOAD_DIR" "$SRC_PARENT" "$BUILD_PARENT" "$ARTIFACT_DIR" "$(dirname "$SOURCE_DIR")"

if [[ ! -f "$TARBALL_PATH" ]]; then
  curl -L "$SOURCE_URL" -o "$TARBALL_PATH"
fi

rm -rf "$SRC_DIR" "$BUILD_DIR" "$SOURCE_DIR"
tar -xf "$TARBALL_PATH" -C "$SRC_PARENT"

cat > "$BUILD_NOTES_PATH" <<EOF
MediaSeg FFmpeg Build Configuration

FFmpeg version: $FFMPEG_VERSION
Source URL: $SOURCE_URL
Source archive: $TARBALL_NAME
Local source modifications: none

Configure command:
./configure ${CONFIGURE_FLAGS[*]}
EOF

cp "$BUILD_NOTES_PATH" "$SRC_DIR/MEDIASEG_BUILD_CONFIGURATION.txt"
tar -C "$SRC_PARENT" -cJf "$SOURCE_BUNDLE_PATH" "ffmpeg-$FFMPEG_VERSION"

cp -R "$SRC_DIR" "$BUILD_DIR"

pushd "$BUILD_DIR" >/dev/null
./configure "${CONFIGURE_FLAGS[@]}"
make -j"$(sysctl -n hw.ncpu)"
make install
popd >/dev/null

echo "$SOURCE_DIR"
