import os
import subprocess
import shutil
import datetime
import sys
from pathlib import Path


MB_BASE = 1000 * 1000

TARGET_MIN_UTILIZATION = 0.90
TARGET_MAX_UTILIZATION = 0.98
MAX_ADJUSTMENTS = 8

def get_runtime_search_roots():
    roots = []

    if hasattr(sys, "_MEIPASS"):
        roots.append(Path(sys._MEIPASS))

    if getattr(sys, "frozen", False):
        try:
            roots.append(Path(sys.executable).resolve().parent.parent / "Resources")
        except Exception:
            pass

    roots.append(Path(__file__).resolve().parent)
    return roots

def find_executable(name):
    candidate_names = [name]
    if name in ("ffmpeg", "ffprobe"):
        candidate_names = [name]

    for root in get_runtime_search_roots():
        for candidate_name in candidate_names:
            for candidate in (
                root / "ffmpeg" / candidate_name,
                root / "Resources" / "ffmpeg" / candidate_name,
                root / "assets" / "runtime" / "ffmpeg" / candidate_name,
            ):
                if candidate.exists():
                    return str(candidate)

    disable_external_lookup = os.environ.get("MEDIASEG_DISABLE_EXTERNAL_FFMPEG_LOOKUP") == "1"
    if disable_external_lookup and name in ("ffmpeg", "ffprobe"):
        return None

    candidates = [
        shutil.which(name),
        f"/opt/homebrew/bin/{name}",
        f"/usr/local/bin/{name}",
    ]
    for candidate in candidates:
        if candidate and os.path.exists(candidate):
            return candidate
    return None

def check_dependencies():
    ffmpeg_path = find_executable("ffmpeg")
    ffprobe_path = find_executable("ffprobe")
    if not ffmpeg_path:
        raise RuntimeError(
            "Missing dependency: ffmpeg is not available. Install ffmpeg and restart MediaSeg."
        )
    if not ffprobe_path:
        raise RuntimeError(
            "Missing dependency: ffprobe is not available. Install ffmpeg/ffprobe and restart MediaSeg."
        )
    return ffmpeg_path, ffprobe_path

def get_duration(file_path, ffprobe_path=None):
    if not ffprobe_path:
        ffprobe_path = find_executable("ffprobe")
        if not ffprobe_path:
            raise RuntimeError(
                "Missing dependency: ffprobe is not available. Install ffmpeg/ffprobe and restart MediaSeg."
            )
    cmd = [
        ffprobe_path, "-v", "error", "-show_entries", "format=duration",
        "-of", "default=nw=1:nk=1", str(file_path)
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    return float(result.stdout.strip())

def split_media(input_file: str, max_size_mb: int = 200, logger=print, output_dir: str = None):
    ffmpeg_path, ffprobe_path = check_dependencies()

    # Resolve input path
    input_file_path = Path(input_file)

    if not input_file_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_file_path}")

    # Generate safe_base_filename (Truncated to 120 chars if extremely long to avoid OS filename length limits)
    base_filename = input_file_path.stem
    if len(base_filename) > 120:
        safe_base_filename = base_filename[:120]
    else:
        safe_base_filename = base_filename

    timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
    outdir_name = f"{safe_base_filename}_{timestamp}"

    if output_dir:
        outdir_path = Path(output_dir) / outdir_name
    else:
        outdir_path = input_file_path.parent / outdir_name

    outdir_path.mkdir(parents=True, exist_ok=True)
    logger(f"Output folder created: {outdir_path}")

    ext = input_file_path.suffix.lower()
    is_webm = ext == ".webm"

    target_file_path = input_file_path
    temp_converted_path = None
    
    try:
        # If input is webm, convert to mp4 first and place in outdir
        if is_webm:
            logger("Converting...")
            temp_converted_path = outdir_path / "_tmp_converted.mp4"
            cmd_convert = [
                ffmpeg_path, "-y", "-i", str(input_file_path),
                "-c:v", "h264_videotoolbox",
                "-pix_fmt", "yuv420p",
                "-tag:v", "avc1",
                "-c:a", "aac", str(temp_converted_path)
            ]
            try:
                subprocess.run(cmd_convert, check=True)
            except subprocess.CalledProcessError as e:
                raise RuntimeError(
                    "Conversion failed: MediaSeg could not convert the WEBM file to MP4."
                ) from e
            target_file_path = temp_converted_path

        # Compute parameters
        try:
            dur_total = get_duration(target_file_path, ffprobe_path)
        except Exception as e:
            raise RuntimeError(f"Duration probe failed: {e}") from e

        import math

        size_bytes = target_file_path.stat().st_size
        size_mb = size_bytes / MB_BASE

        chunk_count = int(math.ceil(size_mb / max_size_mb))
        if chunk_count <= 0:
            chunk_count = 1

        seg_time = dur_total / chunk_count
        if seg_time <= 0:
            seg_time = 1.0

        logger(f"Input Size = {size_mb:.1f} MB")
        logger(f"Target Size = {max_size_mb} MB")
        logger(f"Chunk Count = {chunk_count}")
        logger(f"Segment Time = {seg_time:.1f} sec")

        target_min_mb = max_size_mb * TARGET_MIN_UTILIZATION
        target_max_mb = max_size_mb * TARGET_MAX_UTILIZATION
        logger(f"Target Utilization = {TARGET_MIN_UTILIZATION * 100:.0f}% - {TARGET_MAX_UTILIZATION * 100:.0f}%")
        logger(f"Target Range = {target_min_mb:.1f} MB - {target_max_mb:.1f} MB")
        logger(f"Hard Limit = {max_size_mb:.1f} MB")
        logger("Splitting...")

        max_size_bytes = max_size_mb * MB_BASE
        target_min_bytes = max_size_bytes * TARGET_MIN_UTILIZATION
        target_max_bytes = max_size_bytes * TARGET_MAX_UTILIZATION
        n = 1
        current_start_time = 0.0

        while current_start_time < dur_total:
            remaining_duration = dur_total - current_start_time
            if remaining_duration <= 0:
                break

            cand_dur_int = int(round(min(seg_time, remaining_duration)))
            if cand_dur_int <= 0:
                cand_dur_int = 1

            # Adjust/extract iteratively to fit target range (90%-98%)
            adjustment_count = 0
            best_path = outdir_path / f"_best_{n:03d}.mp4"
            best_bytes = 0
            best_mb = 0.0
            best_distance = None
            out_path = outdir_path / f"{safe_base_filename}_{n:03d}.mp4"

            while True:
                adjustment_count += 1
                if adjustment_count > MAX_ADJUSTMENTS:
                    if best_path.exists() and best_bytes > 0:
                        shutil.copy2(best_path, out_path)
                        utilization = (best_bytes / max_size_bytes) * 100
                        logger(
                            f"Reached max adjustments; using best candidate "
                            f"{best_mb:.1f} MB ({utilization:.1f}%)  -> {out_path.name}"
                        )
                    else:
                        logger(f"Reached max adjustments with no valid candidate for {out_path.name}")
                    break

                remaining_duration = dur_total - current_start_time
                if remaining_duration <= 0:
                    break

                if cand_dur_int >= remaining_duration:
                    cand_dur_int = int(math.ceil(remaining_duration))
                    if cand_dur_int <= 0:
                        break

                is_last_chunk = (current_start_time + cand_dur_int >= dur_total)

                cmd_extract = [
                    ffmpeg_path, "-hide_banner", "-y",
                    "-ss", f"{current_start_time:.3f}",
                    "-i", str(target_file_path),
                    "-t", str(cand_dur_int),
                    "-map", "0", "-c", "copy",
                    "-reset_timestamps", "1", "-avoid_negative_ts", "make_zero",
                    str(out_path)
                ]

                result = subprocess.run(cmd_extract, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                if result.returncode != 0:
                    raise RuntimeError(f"Chunk extraction failed: {out_path.name}")

                if out_path.exists():
                    out_bytes = out_path.stat().st_size
                    out_mb = out_bytes / MB_BASE
                else:
                    out_bytes = 0
                    out_mb = 0

                if 0 < out_bytes <= max_size_bytes:
                    distance = abs(target_max_bytes - out_bytes)
                    if best_distance is None or distance < best_distance:
                        shutil.copy2(out_path, best_path)
                        best_bytes = out_bytes
                        best_mb = out_mb
                        best_distance = distance

                if out_bytes > 0 and out_bytes <= max_size_bytes:
                    if is_last_chunk or (target_min_bytes <= out_bytes <= target_max_bytes):
                        utilization = (out_bytes / max_size_bytes) * 100
                        logger(
                            f"OK  {out_mb:.1f} MB ({utilization:.1f}%)  -> {out_path.name}"
                        )
                        if best_path.exists():
                            best_path.unlink()
                        break

                # Adjust duration up or down.
                # Use target_max_bytes as the preferred upper bound to avoid chunks too close to the hard limit.
                if out_bytes > target_max_bytes:
                    logger(f"Adjusting Down {out_path.name}: {out_mb:.1f} MB > {target_max_mb:.1f} MB")

                    if out_path.exists():
                        out_path.unlink()

                    ratio = target_max_bytes / out_bytes if out_bytes > 0 else 0.9
                    ratio = min(ratio, 0.99)

                    next_dur = int(round(cand_dur_int * ratio * 0.99))
                    if next_dur >= cand_dur_int:
                        next_dur = cand_dur_int - 1

                    if next_dur <= 1:
                        if best_path.exists() and best_bytes > 0:
                            shutil.copy2(best_path, out_path)
                            utilization = (best_bytes / max_size_bytes) * 100
                            logger(
                                f"Cannot reduce further; using best candidate "
                                f"{best_mb:.1f} MB ({utilization:.1f}%)  -> {out_path.name}"
                            )
                            break
                        raise RuntimeError(
                            "Chunk sizing failed: the selected target size is too small for this media."
                        )

                    cand_dur_int = next_dur

                else:  # out_bytes < target_min_bytes and not is_last_chunk
                    logger(f"Adjusting Up   {out_path.name}: {out_mb:.1f} MB < {target_min_mb:.1f} MB")

                    if out_path.exists():
                        out_path.unlink()

                    if out_bytes > 0:
                        ratio_up = target_min_bytes / out_bytes
                    else:
                        ratio_up = 1.15

                    ratio_up = min(ratio_up, 1.12)
                    next_dur = int(round(cand_dur_int * ratio_up))
                    if next_dur <= cand_dur_int:
                        next_dur = cand_dur_int + 1

                    cand_dur_int = next_dur

            if out_path.exists():
                try:
                    actual_dur = get_duration(out_path, ffprobe_path)
                except Exception:
                    actual_dur = float(cand_dur_int)
                current_start_time += actual_dur
                n += 1
            else:
                break

    finally:
        logger("Cleaning temporary files...")
        if temp_converted_path and temp_converted_path.exists():
            try:
                temp_converted_path.unlink()
            except OSError:
                pass
        for pattern in ("_tmp_*.mp4", "_best_*.mp4"):
            for f in outdir_path.glob(pattern):
                try:
                    f.unlink()
                except OSError:
                    pass

    logger("Done.")
    return outdir_path
