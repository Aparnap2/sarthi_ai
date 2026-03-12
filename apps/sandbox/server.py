"""
Saarathi Sandbox — isolated Python execution service.
py-alpine container. No external network. Non-root user.
Every chart request from agents routes here.
"""
from __future__ import annotations
import os
import io
import sys
import base64
import signal
import traceback
import contextlib
from flask import Flask, request, jsonify
import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

app = Flask(__name__)
SECRET = os.getenv("SANDBOX_SECRET", "saarathi-local")
LIMIT = int(os.getenv("MAX_EXECUTION_SECONDS", "15"))

BLOCKED = {
    "open",
    "exec",
    "__import__",
    "compile",
    "breakpoint",
    "input",
    "memoryview",
}


def _safe_globals() -> dict:
    import numpy as np
    import pandas as pd
    import matplotlib.pyplot as plt
    import sklearn
    import scipy
    import math
    import statistics
    from datetime import datetime, date, timedelta
    import matplotlib.ticker as mticker
    import matplotlib.dates as mdates

    raw = (
        __builtins__
        if isinstance(__builtins__, dict)
        else {k: getattr(__builtins__, k) for k in dir(__builtins__)}
    )
    safe = {k: v for k, v in raw.items() if k not in BLOCKED}

    return {
        "__builtins__": safe,
        # data science
        "np": np,
        "numpy": np,
        "pd": pd,
        "pandas": pd,
        "plt": plt,
        "matplotlib": matplotlib,
        "mticker": mticker,
        "mdates": mdates,
        "sklearn": sklearn,
        "scipy": scipy,
        "math": math,
        "statistics": statistics,
        # stdlib
        "datetime": datetime,
        "date": date,
        "timedelta": timedelta,
        "print": print,
        "range": range,
        "enumerate": enumerate,
        "zip": zip,
        "len": len,
        "sum": sum,
        "min": min,
        "max": max,
        "abs": abs,
        "round": round,
        "sorted": sorted,
        "list": list,
        "dict": dict,
        "str": str,
        "int": int,
        "float": float,
        "bool": bool,
    }


class _Timeout(Exception):
    pass


def _alarm(signum, frame):
    raise _Timeout()


@app.before_request
def _auth():
    if request.path == "/health":
        return
    if request.headers.get("X-Sandbox-Secret") != SECRET:
        return jsonify({"error": "unauthorized"}), 401


@app.get("/health")
def health():
    return jsonify({"status": "ok", "service": "saarathi-sandbox"})


@app.post("/execute")
def execute():
    body = request.get_json(force=True)
    code = (body.get("code") or "").strip()
    timeout = min(int(body.get("timeout", 10)), LIMIT)

    if not code:
        return jsonify({"error": "no code provided"}), 400

    stdout_buf = io.StringIO()
    plt.close("all")

    signal.signal(signal.SIGALRM, _alarm)
    signal.alarm(timeout)

    output = ""
    chart_b64 = None
    error = None

    try:
        with contextlib.redirect_stdout(stdout_buf):
            exec(code, _safe_globals())  # noqa: S102
        output = stdout_buf.getvalue()
        if plt.get_fignums():
            img = io.BytesIO()
            plt.savefig(
                img, format="png", dpi=120, bbox_inches="tight", facecolor="white"
            )
            img.seek(0)
            chart_b64 = base64.b64encode(img.read()).decode()
            plt.close("all")
    except _Timeout:
        error = f"Stopped: exceeded {timeout}s limit"
    except Exception:
        tb = traceback.format_exc(limit=4)
        error = tb.replace("/home/sandbox/", "")
    finally:
        signal.alarm(0)

    return jsonify(
        {
            "output": output or "",
            "chart": chart_b64,
            "error": error,
            "success": error is None,
        }
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=False)
