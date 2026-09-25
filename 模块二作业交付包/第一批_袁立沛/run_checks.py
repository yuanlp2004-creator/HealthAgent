"""Run the second member's cases or group checks with reproducible evidence."""
import argparse
from datetime import datetime
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import subprocess
import sys


HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("suite", nargs="?", default="personal",
                        choices=["personal", "module2", "defect-review", "regression"])
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    out = (args.output_dir or HERE / "执行结果" /
           datetime.now().strftime("%Y%m%d_%H%M%S_%f")).resolve()
    out.mkdir(parents=True, exist_ok=True)
    if any((out / name).exists() for name in ["results.log", "results.xml", "environment.json"]):
        parser.error("output directory already contains evidence; select a new directory")
    suites = {
        "personal": ["tests/module2/test_bp_ai.py"],
        "module2": ["tests/module2"],
        "defect-review": ["tests/module2/test_auth_ai.py::test_invalid_credentials_return_401"],
        "regression": ["tests/test_auth.py", "tests/test_users.py", "tests/test_bp_records.py",
                       "tests/test_security.py", str(REPO / "模块一作业交付包" / "缺陷证据" /
                                                    "test_defect_regressions.py")],
    }
    env = os.environ.copy()
    env.update(DATABASE_URL="sqlite://", JWT_SECRET="module-two-isolated-test-key",
               APP_DEBUG="false", PYTHONIOENCODING="utf-8")
    command = [sys.executable, "-m", "pytest", "-v", "-p", "no:cacheprovider",
               "--junitxml=" + str(out / "results.xml"), *suites[args.suite]]
    paths = sorted(set(REPO.glob("backend/app/**/*.py")) |
                   set(REPO.glob("backend/tests/**/*.py")) | {Path(__file__).resolve()})
    metadata = {
        "executed_at": datetime.now().astimezone().isoformat(), "suite": args.suite,
        "revision": subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=REPO, text=True).strip(),
        "worktree_status": subprocess.check_output(
            ["git", "-c", "core.quotepath=false", "status", "--short"], cwd=REPO,
            text=True, encoding="utf-8"),
        "platform": platform.platform(), "python": platform.python_version(),
        "packages": {name: importlib.metadata.version(name) for name in
                     ["pytest", "fastapi", "sqlalchemy", "python-jose"]},
        "command": command,
        "sha256": {path.relative_to(REPO).as_posix(): hashlib.sha256(path.read_bytes()).hexdigest()
                   for path in paths},
        "assistance": "AI-assisted execution; not an independent student review or signature",
    }
    result = subprocess.run(command, cwd=REPO / "backend", env=env, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace")
    (out / "results.log").write_text(result.stdout, encoding="utf-8")
    metadata["exit_code"] = result.returncode
    (out / "environment.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(result.stdout, end="")
    print(f"Evidence: {out}")
    return result.returncode


if __name__ == "__main__":
    raise SystemExit(main())
