import os
import subprocess
import sys
from pathlib import Path


PUBLIC_VERSION = "1.2.0"
BUILD_SHA_ENV_VAR = "MEDIASEG_BUILD_SHA"
BUILD_SHA_FILE_PARTS = ("build", "build_sha.txt")


def _project_root():
    return Path(__file__).resolve().parent


def _bundled_assets_root():
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "assets"
    return _project_root() / "assets"


def _build_sha_file_path():
    return _bundled_assets_root().joinpath(*BUILD_SHA_FILE_PARTS)


def get_public_version():
    return PUBLIC_VERSION


def get_build_version():
    env_value = os.environ.get(BUILD_SHA_ENV_VAR, "").strip()
    if env_value:
        return env_value

    build_sha_file = _build_sha_file_path()
    if build_sha_file.exists():
        text = build_sha_file.read_text(encoding="utf-8").strip()
        if text:
            return text

    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=_project_root(),
            capture_output=True,
            text=True,
            check=True,
        )
        sha = result.stdout.strip()
        if sha:
            return sha
    except Exception:
        pass

    return "unknown"
