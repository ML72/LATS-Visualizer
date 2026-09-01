"""
Run candidate Python in a separate process and report which tests passed.

The environment feedback in the programming task is real: the code the policy
proposes is actually executed. That means it must not be executed *here*. Every
candidate runs in a fresh ``sys.executable`` subprocess with a wall-clock
timeout, so an infinite loop costs a few seconds and a crash costs nothing.

This is a teaching demo, not a sandbox. A subprocess bounds runtime and keeps
the search process's own namespace clean; it does not contain hostile code. The
mock policy only ever proposes code written in ``code_task.py``, but the
``--llm openai`` path will happily run whatever the model wrote - see the
warning in the README before pointing that at anything untrusted.
"""

from __future__ import annotations

import json
import subprocess
import sys

#: Executed in the child process. Reads one JSON object on stdin, writes one on
#: stdout. Kept as a string rather than a file so the package stays importable
#: from anywhere without worrying about data files.
_HARNESS = r'''
import json, sys, traceback

job = json.load(sys.stdin)
ns = {}
results = []
try:
    exec(job["source"], ns)
except Exception:
    err = traceback.format_exc(limit=1).strip().splitlines()[-1]
    print(json.dumps({"ok": False, "error": err, "results": []}))
    sys.exit(0)

for t in job["tests"]:
    try:
        got = eval(t["call"], dict(ns))
        want = eval(t["expect"], {})
        results.append({"call": t["call"], "expect": t["expect"],
                        "got": repr(got), "passed": got == want})
    except Exception:
        err = traceback.format_exc(limit=1).strip().splitlines()[-1]
        results.append({"call": t["call"], "expect": t["expect"],
                        "got": err, "passed": False})

print(json.dumps({"ok": True, "error": None, "results": results}))
'''


def run_tests(source: str, tests: list[dict], timeout: float = 10.0) -> dict:
    """Execute ``source``, then every test call, in a child process.

    Returns ``{"ok", "error", "results", "passed", "total", "fraction"}``.
    ``fraction`` is the reward the programming task backpropagates - the
    paper's "percentage of generated tests passed".
    """
    job = json.dumps({"source": source, "tests": tests})
    try:
        proc = subprocess.run(
            [sys.executable, "-I", "-c", _HARNESS],
            input=job,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
        payload = json.loads(proc.stdout or "{}")
    except subprocess.TimeoutExpired:
        payload = {"ok": False, "error": f"timed out after {timeout:g}s", "results": []}
    except json.JSONDecodeError:
        payload = {"ok": False, "error": "the test runner produced no output",
                   "results": []}

    results = payload.get("results", [])
    passed = sum(1 for r in results if r["passed"])
    total = len(tests)
    payload["passed"] = passed
    payload["total"] = total
    payload["fraction"] = passed / total if total else 0.0
    return payload
