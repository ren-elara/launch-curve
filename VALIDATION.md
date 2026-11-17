# Validation

Evaluated November 17, 2026 on the public comparable histories in the kit's
`input/p00.in`. Each forecast holds out the entire launch being predicted,
including all of its future outcomes. The model receives that launch's history
through hour 1 and the other launches' comparable records.

## Exploratory cross-validation

| Comparable subset | Launches | House baseline loss | Launch Curve loss | Relative reduction | Launch Curve 90% coverage |
| --- | ---: | ---: | ---: | ---: | ---: |
| Console-only | 8 | 0.322556 | 0.190162 | 41.0% | 90.76% |
| First-hour audience at least 10,000 | 28 | 0.350833 | 0.269443 | 23.2% | 82.61% |

Loss is the mean log pinball loss over the five quantiles and available hours,
averaged equally over launches. Lower is better. Each launch is omitted from
both the point model and the residual-calibration training set when it is the
evaluation target. The fallback baseline uses the published widening log-normal
spread around the first-hour count.

Settings were compared on these same public holdouts. These figures therefore
describe model selection, not an untouched test set. The console subset is small,
and its hours are correlated. The broader set includes PC, early-access, and
other launches with different behavior; its 82.61% coverage shows that the
selected intervals can be too narrow outside the console target setting.

Training features use only pre-checkpoint observations. Launch metadata is
parsed from the supplied platforms and unlock descriptions; uncertain metadata
can differ from the scored case's known rolling-midnight console schedule.
GTA VI may have a much larger first-hour audience than any training example.
Historical hourly averages also differ from the final's minute-sampled means.

These are **not official make.fun practice scores** and do not establish a
leaderboard rank or predict a prize. The private practice references and final
answers were not obtained or used.

## Runner checks

The four supplied practice inputs each ran twice in separate processes and
temporary directories. Every output was byte-identical across hash seeds, below
65,536 bytes, and conformed to the exact 23-hour/five-quantile schema. Values
were positive, finite, monotone, and within the one-billion-viewer cap.

The initial runner check measured 1.24–1.33 seconds per real practice case on this
machine. A synthetic final-shaped fixture with 42 comparables and a first-hour
audience of four million ran in 1.44 seconds. The competition permits eight
seconds per case. Synthetic additions test the larger input/runtime shape only;
they do not reproduce unknown final data. The zero-viewer, empty-history
fallback also passed. Runtime measurements used Python 3.12.16; the grader uses
Python 3.13, and the implementation uses standard-library features available in
both versions.

## Submission gate

The working candidate passed make.fun's local worktree checks: 13 passed,
0 failed, 5 skipped, and 5 deferred to submission. This included transcript
format, timestamps, model pricing, run record, revisions, and 100% authored
coverage of counted lines. The final bundle/check should be regenerated after
any further changes. Local checks do not measure forecast accuracy; the
competition's official scorer and practice references remain on the server.
