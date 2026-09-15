"""Lab: how many samples does an eval need before its numbers mean anything?

StyleAI compares prompt versions by scoring outfits 1-5. The scores are noisy:
outfits differ in difficulty, and judges disagree. This lab simulates that
noise to show:

  1. how often a small eval points at the wrong version
  2. how the detection rate grows with the number of items
  3. what scoring the same items with both versions (paired design) buys
  4. how wide a bootstrap confidence interval is at different sizes
  5. what averaging two judges does

Everything here is simulation: no model is called. The point is the shape of
the curves, not the absolute numbers.

Run:  python eval_stats_lab.py   (needs numpy)
"""

from __future__ import annotations

import numpy as np

RNG_SEED = 3
TRIALS = 4000

TRUE_A = 3.90  # average score of prompt v1
TRUE_B = 4.10  # average score of prompt v2: 0.2 better
ITEM_SD = 0.70  # some outfits are simply harder than others
JUDGE_SD = 0.45  # the same outfit scored twice does not get the same score


def clip_scores(x: np.ndarray) -> np.ndarray:
    return np.clip(x, 1.0, 5.0)


def run_unpaired(n: int, rng: np.random.Generator, judges: int = 1) -> float:
    """Different items for each version. Returns observed difference."""
    a_items = rng.normal(TRUE_A, ITEM_SD, size=n)
    b_items = rng.normal(TRUE_B, ITEM_SD, size=n)
    a = clip_scores(a_items[:, None] + rng.normal(0, JUDGE_SD, size=(n, judges))).mean(1)
    b = clip_scores(b_items[:, None] + rng.normal(0, JUDGE_SD, size=(n, judges))).mean(1)
    return b.mean() - a.mean()


def run_paired(n: int, rng: np.random.Generator, judges: int = 1) -> tuple[float, np.ndarray]:
    """Same items scored under both versions; item difficulty cancels out."""
    difficulty = rng.normal(0, ITEM_SD, size=n)
    a = clip_scores(TRUE_A + difficulty[:, None] + rng.normal(0, JUDGE_SD, size=(n, judges))).mean(1)
    b = clip_scores(TRUE_B + difficulty[:, None] + rng.normal(0, JUDGE_SD, size=(n, judges))).mean(1)
    diffs = b - a
    return diffs.mean(), diffs


def detection_rate(n: int, paired: bool, judges: int = 1) -> tuple[float, float]:
    """Share of trials where the better version wins, and where it wins by > 0.05."""
    rng = np.random.default_rng(RNG_SEED + n + (1000 if paired else 0) + judges * 7)
    wins = clear = 0
    for _ in range(TRIALS):
        d = run_paired(n, rng, judges)[0] if paired else run_unpaired(n, rng, judges)
        wins += d > 0
        clear += d > 0.05
    return wins / TRIALS, clear / TRIALS


def bootstrap_ci(diffs: np.ndarray, rng: np.random.Generator, reps: int = 2000) -> tuple[float, float]:
    idx = rng.integers(0, len(diffs), size=(reps, len(diffs)))
    means = diffs[idx].mean(axis=1)
    return float(np.percentile(means, 2.5)), float(np.percentile(means, 97.5))


def main() -> None:
    print(f"simulated eval: v1 mean {TRUE_A}, v2 mean {TRUE_B} (true difference {TRUE_B - TRUE_A:+.2f})")
    print(f"item spread SD {ITEM_SD}, judge noise SD {JUDGE_SD}, {TRIALS} simulated evals per row")

    print("\n[1] one eval with 20 items, different items per version")
    rng = np.random.default_rng(RNG_SEED)
    for i in range(5):
        d = run_unpaired(20, rng)
        verdict = "v2 looks better" if d > 0 else "v1 looks better"
        print(f"  run {i + 1}: observed difference {d:+.3f}  -> {verdict}")

    print("\n[2] how often the eval points at the better version")
    print(f"  {'items':>6}{'unpaired':>11}{'paired':>10}")
    for n in (10, 20, 50, 100, 200, 500):
        u, _ = detection_rate(n, paired=False)
        p, _ = detection_rate(n, paired=True)
        print(f"  {n:>6}{u:>10.1%}{p:>10.1%}")

    print("\n[3] requiring a visible margin (observed difference > 0.05)")
    print(f"  {'items':>6}{'unpaired':>11}{'paired':>10}")
    for n in (20, 50, 100, 200, 500):
        _, u = detection_rate(n, paired=False)
        _, p = detection_rate(n, paired=True)
        print(f"  {n:>6}{u:>10.1%}{p:>10.1%}")

    print("\n[4] bootstrap 95% confidence interval of the paired difference (one eval each)")
    rng = np.random.default_rng(RNG_SEED + 99)
    for n in (20, 50, 100, 200, 500):
        mean, diffs = run_paired(n, rng)
        low, high = bootstrap_ci(diffs, rng)
        covers_zero = "includes 0" if low <= 0 <= high else "excludes 0"
        print(f"  n={n:>4}  mean {mean:+.3f}  CI [{low:+.3f}, {high:+.3f}]  width {high - low:.3f}  {covers_zero}")

    print("\n[5] averaging two judges instead of one (paired design)")
    print(f"  {'items':>6}{'1 judge':>10}{'2 judges':>11}")
    for n in (20, 50, 100, 200):
        one, _ = detection_rate(n, paired=True, judges=1)
        two, _ = detection_rate(n, paired=True, judges=2)
        print(f"  {n:>6}{one:>10.1%}{two:>10.1%}")


if __name__ == "__main__":
    main()
