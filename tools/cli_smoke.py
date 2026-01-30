"""
CLI smoke test (no network).
Runs basic CLI commands and reports failures.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def run_cmd(args: list[str]) -> int:
    result = subprocess.run(args, check=False, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[FAIL] {' '.join(args)}")
        if result.stdout:
            print(result.stdout)
        if result.stderr:
            print(result.stderr, file=sys.stderr)
    else:
        print(f"[OK] {' '.join(args)}")
    return result.returncode


def main() -> int:
    repo_root = Path(__file__).resolve().parents[1]
    csv_path = repo_root / "data" / "stock" / "akshare" / "US.AAPL_AAPL_20211126_20251124.csv"
    errors = 0

    errors += run_cmd([sys.executable, "-m", "core.cli", "strategy", "list"])

    if csv_path.exists():
        errors += run_cmd(
            [
                sys.executable,
                "-m",
                "core.cli",
                "backtest",
                "--csv",
                str(csv_path),
                "--strategy",
                "EnhancedVolumeStrategy",
            ]
        )
    else:
        print(f"[SKIP] CSV not found: {csv_path}")

    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
