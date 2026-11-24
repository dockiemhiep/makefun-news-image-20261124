#!/usr/bin/env python3
"""Entry point for the make.fun news-image-20261124 bounty.

Copies entry.png located beside this script into the output directory
specified by MAKEFUN_OUTPUT_DIR (defaulting to /output).
"""

import os
import shutil


def main() -> None:
    repo_dir = os.path.dirname(os.path.abspath(__file__))
    src_path = os.path.join(repo_dir, "entry.png")

    output_dir = os.environ.get("MAKEFUN_OUTPUT_DIR") or "/output"
    os.makedirs(output_dir, exist_ok=True)
    dst_path = os.path.join(output_dir, "entry.png")

    shutil.copyfile(src_path, dst_path)


if __name__ == "__main__":
    main()
