#!/usr/bin/env python3

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from collections import deque
from pathlib import Path


SYSTEM_PREFIXES = ("/System/Library/", "/usr/lib/")
DEFAULT_FFMPEG_CELLAR = Path("/opt/homebrew/Cellar/ffmpeg/7.1.1_4")


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def parse_deps(binary_path: Path) -> list[str]:
    output = run(["otool", "-L", str(binary_path)])
    deps = []
    for line in output.splitlines()[1:]:
        dep = line.strip().split(" ", 1)[0]
        if dep and not dep.startswith(SYSTEM_PREFIXES):
            deps.append(dep)
    return deps


def resolve_source(path_str: str) -> Path:
    path = Path(path_str)
    try:
        return path.resolve()
    except FileNotFoundError:
        return path


def collect_dependency_closure(seed_paths: list[Path]) -> tuple[dict[Path, list[Path]], set[Path]]:
    deps_map: dict[Path, list[Path]] = {}
    all_paths: set[Path] = set()
    queue: deque[Path] = deque(seed_paths)

    while queue:
        current = resolve_source(str(queue.popleft()))
        if current in all_paths or not current.exists():
            continue

        all_paths.add(current)
        try:
            deps = [resolve_source(dep) for dep in parse_deps(current)]
        except subprocess.CalledProcessError:
            deps = []

        deps_map[current] = deps
        for dep in deps:
            if dep not in all_paths and dep not in queue:
                queue.append(dep)

    return deps_map, all_paths


def copy_bundle_files(source_paths: set[Path], destination_dir: Path) -> dict[Path, Path]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    copied: dict[Path, Path] = {}

    for source_path in sorted(source_paths):
        if not source_path.exists():
            continue
        if any(str(source_path).startswith(prefix) for prefix in SYSTEM_PREFIXES):
            continue

        dest_path = destination_dir / source_path.name
        shutil.copy2(source_path, dest_path)
        if os.access(source_path, os.X_OK):
            dest_path.chmod(dest_path.stat().st_mode | 0o111)
        copied[source_path] = dest_path

    return copied


def patch_bundle(copied_paths: dict[Path, Path], deps_map: dict[Path, list[Path]]) -> None:
    copied_by_name = {src.name: dst for src, dst in copied_paths.items()}

    for src, dst in copied_paths.items():
        if dst.suffix == ".dylib":
            subprocess.run(
                ["install_name_tool", "-id", f"@loader_path/{dst.name}", str(dst)],
                check=True,
            )

    for src, dst in copied_paths.items():
        deps = deps_map.get(src, [])
        for dep in deps:
            dep_dst = copied_by_name.get(dep.name)
            if dep_dst is None:
                continue
            subprocess.run(
                [
                    "install_name_tool",
                    "-change",
                    str(dep),
                    f"@loader_path/{dep_dst.name}",
                    str(dst),
                ],
                check=True,
            )


def bundle_ffmpeg(target_dir: Path, source_dir: Path = DEFAULT_FFMPEG_CELLAR) -> None:
    source_bin_dir = source_dir / "bin"
    ffmpeg = source_bin_dir / "ffmpeg"
    ffprobe = source_bin_dir / "ffprobe"

    if not ffmpeg.exists() or not ffprobe.exists():
        raise FileNotFoundError(f"Expected ffmpeg tools under {source_bin_dir}")

    seed_paths = [ffmpeg, ffprobe]
    deps_map, all_paths = collect_dependency_closure(seed_paths)
    copied = copy_bundle_files(all_paths, target_dir)
    patch_bundle(copied, deps_map)


def main() -> int:
    if len(sys.argv) < 2:
        print("Usage: bundle_ffmpeg.py <target-dir> [source-dir]", file=sys.stderr)
        return 1

    target_dir = Path(sys.argv[1]).expanduser().resolve()
    source_dir = Path(sys.argv[2]).expanduser().resolve() if len(sys.argv) > 2 else DEFAULT_FFMPEG_CELLAR

    bundle_ffmpeg(target_dir, source_dir)
    print(f"Bundled ffmpeg into {target_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
