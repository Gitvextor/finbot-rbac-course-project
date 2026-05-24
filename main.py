#!/usr/bin/env python3
"""
FinBot one-click launcher.
Starts backend (FastAPI) and frontend (Next.js) together.
"""

from __future__ import annotations

import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
BACKEND_DIR = ROOT / "backend"
FRONTEND_DIR = ROOT / "finbot-frontend"

BACKEND_URL = "http://127.0.0.1:8000"
FRONTEND_URL = "http://127.0.0.1:3000"

processes: list[subprocess.Popen] = []


def log(message: str) -> None:
    print(f"[launcher] {message}", flush=True)


def require_paths() -> None:
    if not (BACKEND_DIR / "main.py").exists():
        raise SystemExit(f"Backend not found: {BACKEND_DIR / 'main.py'}")
    if not (FRONTEND_DIR / "package.json").exists():
        raise SystemExit(f"Frontend not found: {FRONTEND_DIR / 'package.json'}")


def ensure_frontend_env() -> None:
    env_file = FRONTEND_DIR / ".env.local"
    if env_file.exists():
        return

    env_file.write_text("NEXT_PUBLIC_API_URL=http://127.0.0.1:8000\n", encoding="utf-8")
    log("Created finbot-frontend/.env.local")


def ensure_frontend_deps() -> None:
    if (FRONTEND_DIR / "node_modules").exists():
        return

    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("npm not found. Install Node.js first.")

    log("Installing frontend dependencies (first run)...")
    subprocess.run([npm, "install"], cwd=FRONTEND_DIR, check=True)


def spawn(name: str, cmd: list[str], cwd: Path, env: dict | None = None) -> subprocess.Popen:
    log(f"Starting {name}: {' '.join(cmd)}")
    run_env = os.environ.copy()
    if env:
        run_env.update(env)
    if sys.platform == "win32":
        return subprocess.Popen(
            cmd,
            cwd=cwd,
            env=run_env,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )
    return subprocess.Popen(cmd, cwd=cwd, env=run_env, preexec_fn=os.setsid)


def stop_all() -> None:
    for proc in processes:
        if proc.poll() is not None:
            continue
        if sys.platform == "win32":
            subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(proc.pid)],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        else:
            os.killpg(os.getpgid(proc.pid), signal.SIGTERM)


def on_exit(signum, frame) -> None:  # noqa: ARG001
    log("Stopping services...")
    stop_all()
    raise SystemExit(0)


def main() -> None:
    require_paths()
    ensure_frontend_env()
    ensure_frontend_deps()

    python = sys.executable
    npm = shutil.which("npm")
    if not npm:
        raise SystemExit("npm not found. Install Node.js first.")

    signal.signal(signal.SIGINT, on_exit)
    if hasattr(signal, "SIGTERM"):
        signal.signal(signal.SIGTERM, on_exit)

    processes.append(
        spawn(
            "backend",
            [python, "main.py"],
            BACKEND_DIR,
            env={"FINBOT_RELOAD": "0"},
        )
    )
    time.sleep(2)
    processes.append(spawn("frontend", [npm, "run", "dev"], FRONTEND_DIR))

    log("Services started.")
    log(f"Backend:  {BACKEND_URL}")
    log(f"Frontend: {FRONTEND_URL}")
    log(f"API docs: {BACKEND_URL}/docs")
    log("Press Ctrl+C to stop both services.")

    try:
        while True:
            for proc in processes:
                code = proc.poll()
                if code is not None:
                    raise SystemExit(f"A service exited unexpectedly (code={code}).")
            time.sleep(1)
    except KeyboardInterrupt:
        on_exit(None, None)


if __name__ == "__main__":
    main()
