"""Compare forecasting methods by holding out entire comparable launches.

No private practice answers are used. Cross-validation targets come only from
the comparable histories provided as public training data in a single case.
"""

import argparse
import json
import math
import statistics
import time
from pathlib import Path
from main import (DEFAULT_CONFIG, LEVELS, training_examples, forecast_distribution,
                  mixture_quantile, weights_for)


def metrics(rows, truth):
    losses, misses, covered = [], [], []
    for hour, quantiles in enumerate(rows, 1):
        if hour not in truth:
            continue
        actual = truth[hour]
        losses.extend(2 * max(tau * (actual - q), (tau - 1) * (actual - q))
                      for tau, q in zip(LEVELS, quantiles))
        misses.append(abs(actual - quantiles[2]))
        covered.append(quantiles[0] <= actual <= quantiles[4])
    return {"loss": statistics.mean(losses),
            "median_miss_pct": 100 * math.expm1(statistics.mean(misses)),
            "coverage90": statistics.mean(covered)}


def analog_distribution(examples, target, bandwidth=1.4, spread=.15):
    weights = weights_for(examples, target, bandwidth)
    result = []
    for hour in range(1, 24):
        pairs = [(row["y"][hour], w) for row, w in zip(examples, weights)
                 if hour in row["y"]]
        centers, ws = zip(*pairs)
        result.append([mixture_quantile(centers, ws, spread, tau) for tau in LEVELS])
    return result


def evaluate(examples, config, subset="all", method="ridge"):
    results = []
    started = time.perf_counter()
    for i, target in enumerate(examples):
        if subset == "console" and not target["x"][5]:
            continue
        if subset == "established" and target["first"] < 10000:
            continue
        train = examples[:i] + examples[i + 1:]
        if method == "ridge":
            predictions = forecast_distribution(train, target["x"], config)
        elif method == "analog":
            predictions = analog_distribution(train, target["x"], config[0], config[2])
        else:
            predictions = [[z * .15 * math.sqrt(h) for z in (-1.645, -.674, 0, .674, 1.645)]
                           for h in range(1, 24)]
        result = metrics(predictions, target["y"])
        result["name"] = target["name"]
        results.append(result)
    return {"method": method, "config": config, "subset": subset,
            "launches": len(results), "seconds": round(time.perf_counter() - started, 3),
            "mean_loss": statistics.mean(r["loss"] for r in results),
            "coverage90": statistics.mean(r["coverage90"] for r in results),
            "rows": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", type=Path)
    parser.add_argument("--subset", choices=["all", "console", "established"], default="console")
    parser.add_argument("--method", choices=["ridge", "analog", "baseline"], default="ridge")
    parser.add_argument("--bandwidth", type=float, default=DEFAULT_CONFIG[0])
    parser.add_argument("--ridge", type=float, default=DEFAULT_CONFIG[1])
    parser.add_argument("--spread", type=float, default=DEFAULT_CONFIG[2])
    parser.add_argument("--residual-scale", type=float, default=DEFAULT_CONFIG[3])
    args = parser.parse_args()
    case = json.loads(args.case.read_text())
    examples = training_examples(case)
    print(json.dumps(evaluate(examples, (args.bandwidth, args.ridge, args.spread,
                                       args.residual_scale),
                              args.subset, args.method), indent=2))


if __name__ == "__main__":
    main()
