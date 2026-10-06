"""Audit exact registry versions; fail on findings or an unavailable audit service."""
import argparse
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requirements", type=Path, default=ROOT / "requirements/all.txt")
    parser.add_argument("--output", type=Path, default=ROOT / "security-report.json")
    args = parser.parse_args()
    # The framework itself is local and has no public advisory identity for this
    # snapshot. Audit registry dependencies, not a same-named public release.
    pins = [line for line in args.requirements.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith(("#", "-e "))]
    if not pins or any("==" not in line for line in pins):
        raise SystemExit("Expected a complete, exact-pinned registry export")
    with tempfile.TemporaryDirectory(prefix="helloagents-security-") as temp:
        path = Path(temp) / "pins.txt"
        path.write_text("\n".join(pins) + "\n", encoding="utf-8")
        result = subprocess.run([sys.executable, "-m", "pip_audit", "--strict", "--no-deps",
                                 "--disable-pip", "-r", str(path), "--format", "json",
                                 "--output", str(args.output)])
        raise SystemExit(result.returncode)


if __name__ == "__main__":
    main()
