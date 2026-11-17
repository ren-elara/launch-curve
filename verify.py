"""Exercise the actual runner on isolated cases, checking the wire contract."""

import argparse
import hashlib
import json
import math
import os
import subprocess
import sys
import tempfile
import time
from copy import deepcopy
from pathlib import Path

from main import forecast, hourly_table, timestamp


def validate(data):
    assert set(data) == {"hours"}
    assert len(data["hours"]) == 23
    assert sorted(row["hour"] for row in data["hours"]) == list(range(2, 25))
    for row in data["hours"]:
        assert set(row) == {"hour", "q"}
        assert len(row["q"]) == 5
        assert all(isinstance(q, (int, float)) and math.isfinite(q) and 0 < q <= 1e9
                   for q in row["q"])
        assert row["q"] == sorted(row["q"])


def run_isolated(case, filename):
    entry = Path(__file__).resolve().parent / "main.py"
    with tempfile.TemporaryDirectory(prefix="launch-curve-") as temp:
        root = Path(temp)
        source = root / "input"
        source.mkdir()
        (source / filename).write_text(json.dumps(case))
        outputs = []
        elapsed = []
        for run in range(2):
            output = root / f"out-{run}"
            output.mkdir()
            env = dict(os.environ, MAKEFUN_INPUT_DIR=str(source),
                       MAKEFUN_OUTPUT_DIR=str(output), PYTHONHASHSEED=str(run))
            started = time.perf_counter()
            subprocess.run([sys.executable, "-P", "-s", str(entry)], env=env,
                           cwd=root, check=True, timeout=8, capture_output=True)
            elapsed.append(time.perf_counter() - started)
            expected = output / (Path(filename).stem + ".out")
            assert sorted(p.name for p in output.iterdir()) == [expected.name]
            data = expected.read_bytes()
            assert len(data) <= 65536 and not expected.is_symlink()
            validate(json.loads(data))
            outputs.append(data)
        assert outputs[0] == outputs[1], "Repeated runs produced different forecasts"
        return {"case": case["id"], "max_seconds": round(max(elapsed), 4),
                "bytes": len(outputs[0]), "sha256": hashlib.sha256(outputs[0]).hexdigest()}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    args = parser.parse_args()
    cases = sorted(args.input.glob("*.in"))
    assert cases, "No supplied cases"
    results = []
    for path in cases:
        results.append(run_isolated(json.loads(path.read_text()), path.name))

    base = json.loads(cases[0].read_text())
    empty = deepcopy(base)
    empty.update(id="empty-history", comparables=[], history=[], history_hourly=[])
    empty["known"][0]["viewers"] = 0
    validate(forecast(empty))
    results.append(run_isolated(empty, "empty-history.in"))

    # Data arriving at/after the checkpoint cannot affect a launch's features.
    day, checkpoint = timestamp(base["day_start"]), timestamp(base["checkpoint"])
    rows = [{"at": base["day_start"], "viewers": 100},
            {"at": base["checkpoint"], "viewers": 999999}]
    assert hourly_table(rows, day, checkpoint) == {0: 100.0}

    # Changing a display name or case id cannot select a special-case forecast.
    renamed = deepcopy(base)
    renamed["id"] = "unseen-launch"
    renamed["game"]["name"] = "Unseen console release"
    assert forecast(renamed) == forecast(base)

    # The next day's target observations must not become model inputs.
    future = deepcopy(base)
    for key in ("history", "history_hourly"):
        future.setdefault(key, []).append({"at": base["checkpoint"],
                                          "from": base["checkpoint"],
                                          "viewers": 999999999, "channels": 10000,
                                          "reads": 60})
    assert forecast(future) == forecast(base)

    # Exercise the larger 42-comparable final shape without assuming the four
    # additional launches' answers. Synthetic extras test shape/runtime only.
    final_shape = deepcopy(base)
    final_shape["id"] = "final-shape"
    final_shape["known"][0]["viewers"] = 4000000
    for index, comparable in enumerate(base["comparables"][:4]):
        extra = deepcopy(comparable)
        extra["name"] += f" (runtime fixture {index})"
        final_shape["comparables"].append(extra)
    results.append(run_isolated(final_shape, "final-shape.in"))
    print(json.dumps({"passed": True, "cases": results,
                      "checks": ["exact output schema", "strictly positive sorted quantiles",
                                 "byte-identical repeated isolated runs", "8-second case budget",
                                 "empty history and zero-viewer fallback", "checkpoint boundary",
                                 "invariant to target names and case ids",
                                 "future target observations ignored",
                                 "42-comparable final shape at 4 million first-hour viewers"]}, indent=2))


if __name__ == "__main__":
    main()
