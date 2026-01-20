#!/usr/bin/env python3
"""Cross-platform launcher for Alpaca MCP Server."""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path


def find_uv() -> str | None:
    """Find uv executable on the system."""
    # Check if uv is in PATH
    uv_path = shutil.which("uv")
    if uv_path:
        return uv_path

    # Common installation locations by platform
    home = Path.home()
    candidates = []

    if sys.platform == "win32":
        candidates = [
            home / ".cargo" / "bin" / "uv.exe",
            home / ".local" / "bin" / "uv.exe",
            Path(os.environ.get("LOCALAPPDATA", "")) / "uv" / "uv.exe",
        ]
    elif sys.platform == "darwin":
        candidates = [
            home / ".cargo" / "bin" / "uv",
            home / ".local" / "bin" / "uv",
            Path("/opt/homebrew/bin/uv"),
            Path("/usr/local/bin/uv"),
        ]
    else:  # Linux and others
        candidates = [
            home / ".cargo" / "bin" / "uv",
            home / ".local" / "bin" / "uv",
            Path("/usr/local/bin/uv"),
            Path("/usr/bin/uv"),
        ]

    for candidate in candidates:
        if candidate.exists() and candidate.is_file():
            return str(candidate)

    return None


def main() -> int:
    """Launch the Alpaca MCP server using uv."""
    # Change to script directory
    script_dir = Path(__file__).parent.resolve()
    os.chdir(script_dir)

    # Find uv
    uv_path = find_uv()
    if not uv_path:
        print("Error: uv not found.", file=sys.stderr)
        print("Install uv: https://docs.astral.sh/uv/getting-started/installation/", file=sys.stderr)
        return 1

    # Build command
    cmd = [uv_path, "run", "alpaca-mcp-server"] + sys.argv[1:]

    # Execute
    if sys.platform == "win32":
        # On Windows, use subprocess to avoid issues with exec
        result = subprocess.run(cmd)
        return result.returncode
    else:
        # On Unix, replace the current process
        os.execv(uv_path, cmd)


if __name__ == "__main__":
    sys.exit(main())
