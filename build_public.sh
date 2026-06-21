#!/bin/bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT_DIR"
source .venv/bin/activate
mkdir -p assets/build
git rev-parse --short HEAD > assets/build/build_sha.txt
pyinstaller --clean -y MediaSeg.spec
