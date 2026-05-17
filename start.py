"""Launch FastAPI + Streamlit together.

Usage:
    python start.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import threading
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent
os.environ.setdefault("PYTHONPATH", str(ROOT))


def run_api() -> None:
    subprocess.run([
        sys.executable, "-m", "uvicorn",
        "api.main:app",
        "--host", "0.0.0.0",
        "--port", "8000",
        "--reload",
    ], cwd=str(ROOT))


def run_dashboard() -> None:
    time.sleep(3)
    subprocess.run([
        sys.executable, "-m", "streamlit",
        "run", str(ROOT / "dashboard" / "app.py"),
        "--server.port", "8501",
        "--server.address", "0.0.0.0",
        "--theme.base", "dark",
        "--theme.backgroundColor", "#0b0b0b",
        "--theme.secondaryBackgroundColor", "#141414",
        "--theme.primaryColor", "#00C896",
        "--theme.textColor", "#e8e8e8",
        "--browser.gatherUsageStats", "false",
    ], cwd=str(ROOT))


if __name__ == "__main__":
    print("=" * 60)
    print(" Supply Chain Anomaly Detector — Project 4")
    print(" FastAPI  → http://localhost:8000/docs")
    print(" Dashboard → http://localhost:8501")
    print("=" * 60)
    api_thread = threading.Thread(target=run_api, daemon=True)
    api_thread.start()
    try:
        run_dashboard()
    except KeyboardInterrupt:
        print("\nShutting down…")
