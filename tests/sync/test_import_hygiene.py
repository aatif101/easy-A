"""The worker must stay inside its memory budget: no pandas and nothing from easy_a.refresh."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

_PROBE = """
import json
import sys

import easy_a.sync.cli
import easy_a.sync.sweep
# refresh_section_rankings imports these lazily at call time, so the worker loads them too.
import easy_a.rankings.models
import easy_a.rankings.service

print(json.dumps({
    "pandas": "pandas" in sys.modules,
    "refresh": sorted(name for name in sys.modules if name.startswith("easy_a.refresh")),
}))
"""


def test_worker_import_graph_excludes_pandas_and_easy_a_refresh() -> None:
    result = subprocess.run(
        [sys.executable, "-c", _PROBE],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=120,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    report = json.loads(result.stdout.strip().splitlines()[-1])
    assert report["pandas"] is False
    assert report["refresh"] == []
