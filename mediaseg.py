import sys
import argparse
from mediaseg_core import split_media
from mediaseg_version import get_public_version, get_build_version

# --- Configuration ---
MAX_SIZE_MB = 200
# ---------------------

def parse_args():
    parser = argparse.ArgumentParser(
        description="Split media files into upload-size-friendly chunks."
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"MediaSeg {get_public_version()} ({get_build_version()})",
    )
    parser.add_argument(
        "input_file",
        help="Input media file path. Relative paths are resolved from the default input directory.",
    )
    parser.add_argument(
        "--max-size",
        type=int,
        default=MAX_SIZE_MB,
        help="Maximum output chunk size in decimal MB. Default: %(default)s",
    )
    return parser.parse_args()

def main():
    args = parse_args()
    try:
        split_media(args.input_file, args.max_size)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
