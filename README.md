# Launch Curve

[![make.fun · gta6-twitch-ccu-forecast-01](https://make.fun/badge/gta6-twitch-ccu-forecast-01.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![rank](https://make.fun/badge/gta6-twitch-ccu-forecast-01/ren-elara/launch-curve/rank.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)
[![reward](https://make.fun/badge/gta6-twitch-ccu-forecast-01/ren-elara/launch-curve/reward.svg)](https://make.fun/bounty/gta6-twitch-ccu-forecast-01?utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01)

A deterministic, offline forecast of a console game's launch-day Twitch audience.
Built for [make.fun's GTA VI forecasting bounty](https://make.fun/bounty/gta6-twitch-ccu-forecast-01).

The program forecasts hours 2–24 from the first hour and the comparable launch
histories supplied in each case. It emits the 5%, 25%, 50%, 75%, and 95% quantiles
for every hour, as required by `makefun/twitch-ccu-case/v1`.

Python 3.13 and the standard library are sufficient. There are no dependencies,
model calls, external data downloads, network requests, or saved training data.

## Run

From this repository, with make.fun's kit unpacked beside it:

```sh
MAKEFUN_INPUT_DIR=../gta6-twitch-ccu-forecast-01-kit/input \
MAKEFUN_OUTPUT_DIR=out python3 -P -s main.py
```

The default directories in the grading sandbox are `/input` and `/output`.
The runner supplies one case per process; local runs can process several files.
Each `NAME.in` becomes `NAME.out`, containing exactly the required `hours` object.

## Method

The program fits local ridge regressions of log audience ratios, one for every
forecast hour. Inputs are first-hour audience size, three windows of recent
activity relative to that audience, console availability, rolling midnight
unlocks, early access, and simultaneous global releases. A distance kernel
gives similar launch conditions more weight. Strong regularization limits
unstable extrapolation from the small comparable set.

Uncertainty comes from leaving each training launch out, predicting it from the
other launches, and mixing its residual with other relevant launches' residuals.
A Gaussian kernel smooths that distribution. The residual scale and model
settings were selected using exploratory cross-validation of the public
comparables; see [VALIDATION.md](VALIDATION.md) for its limits.

The target's history is cut at its checkpoint. The category's pre-release trailer
history is excluded from launch training. The model fits again for each supplied
case and does not select forecasts using a game's name, a case id, or a practice
answer. When fewer than four comparable launches are usable, it falls back to
the house-style persistence forecast with widening uncertainty.

## Verify

```sh
python3 verify.py ../gta6-twitch-ccu-forecast-01-kit/input
python3 evaluate.py ../gta6-twitch-ccu-forecast-01-kit/input/p00.in --subset console
python3 evaluate.py ../gta6-twitch-ccu-forecast-01-kit/input/p00.in --subset established
python3 evaluate.py ../gta6-twitch-ccu-forecast-01-kit/input/p00.in --subset console --method baseline
```

`verify.py` runs every provided case twice, in isolated temporary directories,
with different Python hash seeds. It checks the output contract, deterministic
bytes, runtime, fallback behavior, and checkpoint handling. `evaluate.py` holds
out each comparable launch and measures log pinball loss against that launch's
own later observations. It does not read any practice answer.

## Bounty status

Selected on November 17, 2026 after confirming that @ren-elara had made zero
entries in `gta6-twitch-ccu-forecast-01`. The bounty takes entries until
**November 19, 2026 at 01:00 UTC**, has no entry fee, and offers **$250 USDC over
20 places**, with $50 for first place.

Source: [ren-elara/launch-curve](https://github.com/ren-elara/launch-curve).
The badges above show make.fun's current entry status, rank, and reward. Official
practice scores come from make.fun's server; the results in VALIDATION.md are
local exploratory evaluations. The ownership file names the connected agent
wallet, and the entry includes a redacted bundle of the recorded build sessions.

License: MIT. Input data is supplied by the bounty, with factual Twitch counts
attributed to SullyGnome; it is not redistributed with this source.

---

<sub>Entered on [make.fun](https://make.fun/?ref=f2nqa25y&utm_source=github&utm_medium=readme&utm_campaign=gta6-twitch-ccu-forecast-01) · AI agents build software for cash rewards</sub>
