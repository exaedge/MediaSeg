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
BUILD_INFO_FILENAME = "FFMPEG_BUILD_INFO.txt"


def run(cmd: list[str]) -> str:
    result = subprocess.run(cmd, check=True, capture_output=True, text=True)
    return result.stdout


def parse_deps(binary_path: Path) -> list[Path]:
    output = run(["otool", "-L", str(binary_path)])
    deps = []
    for line in output.splitlines()[1:]:
        dep = line.strip().split(" ", 1)[0]
        if dep and not dep.startswith(SYSTEM_PREFIXES):
            deps.append(Path(dep))
    return deps


def get_buildconf(binary_path: Path) -> str:
    result = subprocess.run(
        [str(binary_path), "-buildconf"],
        check=True,
        capture_output=True,
        text=True,
    )
    return result.stdout


def ensure_lgpl_compatible(binary_path: Path) -> None:
    buildconf = get_buildconf(binary_path)
    if "--enable-gpl" in buildconf or "--enable-nonfree" in buildconf:
        raise RuntimeError(
            f"{binary_path} is not LGPL-compatible for MediaSeg release bundling."
        )


def write_build_info(target_dir: Path, ffmpeg_path: Path, ffprobe_path: Path) -> None:
    version_result = subprocess.run(
        [str(ffmpeg_path), "-version"],
        check=True,
        capture_output=True,
        text=True,
    )
    buildconf_text = get_buildconf(ffmpeg_path)
    info_path = target_dir / BUILD_INFO_FILENAME
    info_path.write_text(
        "\n".join(
            [
                "MediaSeg bundled FFmpeg runtime",
                "",
                f"ffmpeg binary: {ffmpeg_path}",
                f"ffprobe binary: {ffprobe_path}",
                "",
                version_result.stdout.strip(),
                "",
                buildconf_text.strip(),
                "",
            ]
        ),
        encoding="utf-8",
    )


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
            deps = parse_deps(current)
        except subprocess.CalledProcessError:
            deps = []

        deps_map[current] = deps
        for dep in deps:
            dep_resolved = resolve_source(str(dep))
            if dep_resolved not in all_paths and dep_resolved not in queue:
                queue.append(dep_resolved)

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


def collect_aliases(source_dir: Path, copied_paths: dict[Path, Path]) -> dict[Path, list[str]]:
    aliases: dict[Path, list[str]] = {src: [] for src in copied_paths}
    if not source_dir.exists():
        return aliases

    for entry in source_dir.iterdir():
        if not entry.is_symlink():
            continue
        resolved = resolve_source(str(entry))
        if resolved in aliases:
            aliases[resolved].append(entry.name)

    return aliases


def preferred_install_name(src: Path, alias_names: list[str]) -> str:
    if not alias_names:
        return src.name

    major_aliases = [name for name in alias_names if name.count(".") >= 2]
    if major_aliases:
        major_aliases.sort(key=len, reverse=True)
        return major_aliases[0]

    return alias_names[0]


def create_alias_symlinks(
    copied_paths: dict[Path, Path],
    alias_map: dict[Path, list[str]],
    destination_dir: Path,
) -> None:
    for src, dst in copied_paths.items():
        for alias_name in alias_map.get(src, []):
            alias_path = destination_dir / alias_name
            if alias_path.exists() or alias_path.is_symlink():
                alias_path.unlink()
            alias_path.symlink_to(dst.name)


def patch_bundle(
    copied_paths: dict[Path, Path],
    deps_map: dict[Path, list[Path]],
    alias_map: dict[Path, list[str]],
) -> None:
    copied_by_resolved = {src: dst for src, dst in copied_paths.items()}

    for src, dst in copied_paths.items():
        if dst.suffix == ".dylib":
            install_name = preferred_install_name(src, alias_map.get(src, []))
            subprocess.run(
                ["install_name_tool", "-id", f"@loader_path/{install_name}", str(dst)],
                check=True,
            )

    for src, dst in copied_paths.items():
        deps = deps_map.get(src, [])
        for dep in deps:
            dep_resolved = resolve_source(str(dep))
            dep_dst = copied_by_resolved.get(dep_resolved)
            if dep_dst is None:
                continue
            subprocess.run(
                [
                    "install_name_tool",
                    "-change",
                    str(dep),
                    f"@loader_path/{dep.name}",
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

    ensure_lgpl_compatible(ffmpeg)

    seed_paths = [ffmpeg, ffprobe]
    deps_map, all_paths = collect_dependency_closure(seed_paths)
    copied = copy_bundle_files(all_paths, target_dir)
    alias_map = collect_aliases(source_dir / "lib", copied)
    create_alias_symlinks(copied, alias_map, target_dir)
    patch_bundle(copied, deps_map, alias_map)
    write_build_info(target_dir, ffmpeg, ffprobe)


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
