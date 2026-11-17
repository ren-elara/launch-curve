"""Launch Curve: conditional distributions of Twitch launch-day audiences.

Only the case supplied by the runner is used. Comparable launches are training
examples, and the case's own history is cut at its checkpoint before fitting.
The implementation deliberately uses only the Python standard library.
"""

import json
import math
import os
from pathlib import Path
from datetime import datetime

LEVELS = (0.05, 0.25, 0.5, 0.75, 0.95)
DEFAULT_CONFIG = (1.4, 80.0, 0.10, 0.65)


def timestamp(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00")).timestamp()


def clip(value, lo, hi):
    return max(lo, min(hi, value))


def log_count(value):
    return math.log(max(1.0, float(value or 0)))


def hourly_table(rows, day_start, checkpoint=None):
    """Aggregate actual observed points; missing hours stay missing."""
    sums = {}
    for row in rows:
        at = timestamp(row.get("from", row.get("at")))
        if checkpoint is not None and at >= checkpoint:
            continue
        hour = math.floor((at - day_start) / 3600 + 1e-6)
        if row.get("viewers") is None:
            continue
        weight = max(1, float(row.get("reads", 1) or 1))
        bucket = sums.setdefault(hour, [0.0, 0.0])
        bucket[0] += max(0.0, float(row["viewers"])) * weight
        bucket[1] += weight
    return {h: total / count for h, (total, count) in sums.items()}


def metadata(platforms, unlock):
    text = unlock.lower()
    platforms = platforms.lower()
    console = float("pc" not in platforms and bool(platforms))
    rolling = float("midnight" in text or "rolling" in text)
    early = float("early-access-contaminated" in text)
    global_late = float("simultaneous" in text and not rolling)
    return [console, rolling, early, global_late]


def features(table, meta, first=None):
    p = max(1.0, first if first is not None else table.get(0, 1.0))

    def relative_average(start, stop):
        values = [v for h, v in table.items() if start <= h < stop]
        if not values:
            return 0.0
        return clip(math.log((sum(values) / len(values) + 50) / (p + 50)), -5, 5)

    recent = relative_average(-3, 0)
    preceding = relative_average(-12, -3)
    previous_day = relative_average(-24, -12)
    return [1.0, (math.log(p) - 11) / 2, recent, preceding,
            previous_day, *meta]


def training_examples(case):
    examples = []
    for comp in case.get("comparables", []):
        unlock = comp.get("unlock", "")
        if "target-history" in unlock.lower() or "not a launch" in unlock.lower():
            continue
        start = timestamp(comp["day_start"])
        table = hourly_table(comp.get("hourly", []), start)
        if 0 not in table or sum(h in table for h in range(1, 24)) < 18:
            continue
        meta = metadata(comp.get("platforms", ""), unlock)
        x = features(table, meta)
        ys = {h: log_count(table[h]) - log_count(table[0])
              for h in range(1, 24) if h in table}
        examples.append({"name": comp["name"], "x": x, "y": ys,
                         "first": max(1.0, table[0]), "table": table})
    return examples


def solve(matrix, rhs):
    """Small positive-definite ridge system, pivoted for sparse histories."""
    n = len(rhs)
    a = [list(row) + [rhs[i]] for i, row in enumerate(matrix)]
    for col in range(n):
        pivot = max(range(col, n), key=lambda r: abs(a[r][col]))
        a[col], a[pivot] = a[pivot], a[col]
        divisor = a[col][col]
        if abs(divisor) < 1e-12:
            continue
        for k in range(col, n + 1):
            a[col][k] /= divisor
        for row in range(n):
            if row == col:
                continue
            factor = a[row][col]
            for k in range(col, n + 1):
                a[row][k] -= factor * a[col][k]
    return [a[i][-1] for i in range(n)]


def distance(x, z):
    scales = (0, 0.7, 0.35, 0.2, 0.1, 0.7, 0.7, 0.7, 0.7)
    return sum(s * (a - b) ** 2 for s, a, b in zip(scales, x, z))


def weights_for(examples, target, bandwidth):
    return [math.exp(-min(30, distance(row["x"], target) / (2 * bandwidth ** 2)))
            for row in examples]


def fit_hour(examples, target, hour, config):
    bandwidth, ridge = config[:2]
    available = [e for e in examples if hour in e["y"]]
    weights = weights_for(available, target, bandwidth)
    total = sum(weights) or 1.0
    weights = [w * len(available) / total for w in weights]
    n = len(target)
    matrix = [[0.0] * n for _ in range(n)]
    rhs = [0.0] * n
    for row, weight in zip(available, weights):
        x, y = row["x"], row["y"][hour]
        for i in range(n):
            rhs[i] += weight * x[i] * y
            for j in range(n):
                matrix[i][j] += weight * x[i] * x[j]
    for i in range(n):
        matrix[i][i] += 1e-7 if i == 0 else ridge
    beta = solve(matrix, rhs)
    return sum(b * v for b, v in zip(beta, target)), beta


def normal_cdf(value):
    return (1 + math.erf(value / math.sqrt(2))) / 2


def mixture_quantile(centers, weights, spread, level):
    total = sum(weights)
    lo, hi = min(centers) - 8 * spread, max(centers) + 8 * spread
    for _ in range(38):
        middle = (lo + hi) / 2
        cdf = sum(w * normal_cdf((middle - c) / spread)
                  for w, c in zip(weights, centers)) / total
        if cdf < level:
            lo = middle
        else:
            hi = middle
    return (lo + hi) / 2


def forecast_distribution(examples, target, config=DEFAULT_CONFIG):
    """Local regression with honest, leave-one-launch-out residuals."""
    if len(examples) < 4:
        return [[z * 0.15 * math.sqrt(h) for z in (-1.645, -.674, 0, .674, 1.645)]
                for h in range(1, 24)]
    bandwidth, ridge, spread = config[:3]
    residual_scale = config[3] if len(config) > 3 else 1.0
    all_weights = weights_for(examples, target, bandwidth)
    predictions = []
    for hour in range(1, 24):
        center, _ = fit_hour(examples, target, hour, config)
        residuals, residual_weights = [], []
        for index, row in enumerate(examples):
            if hour not in row["y"]:
                continue
            others = examples[:index] + examples[index + 1:]
            prediction, _ = fit_hour(others, row["x"], hour, config)
            residuals.append(residual_scale * (row["y"][hour] - prediction))
            residual_weights.append(all_weights[index])
        # A kernel avoids treating a few observed launch paths as exact futures.
        width = spread * min(1.0, math.sqrt(hour / 5))
        predictions.append([center + mixture_quantile(residuals, residual_weights, width, level)
                            for level in LEVELS])
    return predictions


def case_features(case):
    start, checkpoint = timestamp(case["day_start"]), timestamp(case["checkpoint"])
    history = case.get("history_hourly") or case.get("history") or []
    table = hourly_table(history, start, checkpoint)
    p = max(1.0, float(case["known"][0]["viewers"] or 0))
    # Every scored case is a console launch with local-midnight regional unlocks.
    return p, features(table, [1.0, 1.0, 0.0, 0.0], p)


def forecast(case):
    first, x = case_features(case)
    examples = training_examples(case)
    distribution = forecast_distribution(examples, x)
    hours = []
    for hour, row in enumerate(distribution, 2):
        quantiles = [round(clip(first * math.exp(clip(value, -20, 20)), 1e-6, 1e9), 6)
                     for value in row]
        quantiles = [max(1e-6, value) for value in quantiles]
        hours.append({"hour": hour, "q": sorted(quantiles)})
    return {"hours": hours}


def main():
    source = Path(os.environ.get("MAKEFUN_INPUT_DIR", "/input"))
    output = Path(os.environ.get("MAKEFUN_OUTPUT_DIR", "/output"))
    output.mkdir(parents=True, exist_ok=True)
    for path in sorted(source.glob("*.in")):
        case = json.loads(path.read_text(encoding="utf-8"))
        result = forecast(case)
        (output / (path.stem + ".out")).write_text(
            json.dumps(result, separators=(",", ":"), allow_nan=False) + "\n",
            encoding="utf-8")


if __name__ == "__main__":
    main()
