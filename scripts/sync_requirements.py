"""Export pip installation files from uv.lock; never maintain a second resolver input."""
import argparse
from pathlib import Path
import subprocess
try:
    import tomllib
except ModuleNotFoundError:
    import tomli as tomllib

ROOT = Path(__file__).resolve().parents[1]


def exports():
    project = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    yield Path("requirements.txt"), []
    for extra in sorted(project["project"]["optional-dependencies"]):
        yield Path("requirements") / f"{extra}.txt", ["--extra", extra]
    yield Path("requirements/all.txt"), ["--all-extras"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Fail on stale or missing exports")
    parser.add_argument("--uv", default="uv", help="uv executable")
    args = parser.parse_args()
    stale = []
    for relative, flags in exports():
        result = subprocess.run(
            [args.uv, "export", "--locked", "--no-default-groups", "--format", "requirements.txt",
             "--no-hashes", "--no-header", "--no-annotate", *flags],
            cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
        )
        if result.returncode:
            raise SystemExit(result.stderr.strip() or f"uv export failed: {relative}")
        content = ("# Generated from uv.lock. Run scripts/sync_requirements.py to update.\n"
                   "# Install from the repository root, not from this file's directory.\n"
                   + result.stdout.replace("\r\n", "\n").strip() + "\n")
        path = ROOT / relative
        if args.check:
            if not path.exists() or path.read_text(encoding="utf-8") != content:
                stale.append(str(relative))
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding="utf-8", newline="\n")
    if stale:
        raise SystemExit("Outdated requirements: " + ", ".join(stale))
    print("Requirements exports match uv.lock." if args.check else "Requirements exports updated.")


if __name__ == "__main__":
    main()
