#!/usr/bin/env python3
"""One-command entry point for the required results and added combination tables."""

from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parent

if __name__ == "__main__":
    subprocess.run([sys.executable, str(ROOT / "analyze_field_error_cooccurrence.py")], check=True)
    print(f"Open {ROOT / 'results' / 'field_error_cooccurrence.pdf'}")
