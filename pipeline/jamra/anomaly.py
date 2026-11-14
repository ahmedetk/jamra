"""Anomaly categories, early-warning levels, season start and trend tests.

The same rules are implemented in the website (web/js/stats.js) so numbers on
screen match the pipeline. Code written with an AI coding assistant (Claude Code by Anthropic).
"""
from __future__ import annotations

import math
from statistics import median


def quantile(values: list[float], q: float) -> float | None:
    """Linear-interpolated quantile (q in 0..1), like numpy's default."""
    xs = sorted(v for v in values if v is not None)
    if not xs:
        return None
    pos = (len(xs) - 1) * q
    lo = math.floor(pos)
    hi = math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def percentile_rank(value: float, others: list[float]) -> float | None:
    """Share of other years below this value (ties count half), in percent."""
    xs = [v for v in others if v is not None]
    if not xs or value is None:
        return None
    below = sum(1 for v in xs if v < value)
    equal = sum(1 for v in xs if v == value)
    return 100.0 * (below + 0.5 * equal) / len(xs)


def baseline(others: list[float]) -> dict | None:
    xs = [v for v in others if v is not None]
    if not xs:
        return None
    return {"median": median(xs), "p25": quantile(xs, 0.25), "p75": quantile(xs, 0.75), "n": len(xs)}


def passes_small_count_guard(value: float, med: float, min_abs: float = 3, min_rel: float = 0.2) -> bool:
    return abs(value - med) >= max(min_abs, min_rel * med)


CATEGORIES = ["much_lower", "lower", "typical", "higher", "much_higher"]


def category(value: float | None, others: list[float], cfg: dict) -> str | None:
    """Percentile-rank category with the small-count guard (see config.yaml)."""
    if value is None:
        return None
    b = baseline(others)
    if b is None:
        return None
    pr = percentile_rank(value, others)
    c = cfg["categories"]
    guard = passes_small_count_guard(value, b["median"], cfg["small_count_min_abs"], cfg["small_count_min_rel"])
    if pr >= c["much_higher"] and guard:
        return "much_higher"
    if pr >= c["higher"] and guard:
        return "higher"
    if pr <= c["much_lower"] and guard:
        return "much_lower"
    if pr <= c["lower"] and guard:
        return "lower"
    return "typical"


def warning_level(mtd: float, others_mtd: list[float], cfg: dict) -> dict:
    """Early-warning level for a month-to-date count vs. other years up to the same day."""
    b = baseline(others_mtd)
    if b is None:
        return {"level": "unknown"}
    pr = percentile_rank(mtd, others_mtd)
    lv = cfg["warning_levels"]
    guard = passes_small_count_guard(mtd, b["median"], cfg["small_count_min_abs"], cfg["small_count_min_rel"])
    level = "normal"
    if guard and mtd > b["median"]:
        if pr >= lv["extreme"]:
            level = "extreme"
        elif pr >= lv["high"]:
            level = "high"
        elif pr >= lv["elevated"]:
            level = "elevated"
    return {"level": level, "percentile": pr, "median": b["median"], "p25": b["p25"], "p75": b["p75"], "n_years": b["n"]}


def season_start(monthly: list[float], share: float = 0.10, min_total: float = 20) -> int | None:
    """First month (1-12) when cumulative hotspots reach `share` of the year's total."""
    vals = [v or 0 for v in monthly]
    total = sum(vals)
    if total < min_total:
        return None
    acc = 0.0
    for i, v in enumerate(vals):
        acc += v
        if acc >= share * total:
            return i + 1
    return None


def theil_sen(xs: list[float], ys: list[float]) -> float | None:
    slopes = [(ys[j] - ys[i]) / (xs[j] - xs[i])
              for i in range(len(xs)) for j in range(i + 1, len(xs)) if xs[j] != xs[i]]
    return median(slopes) if slopes else None


def mann_kendall(ys: list[float]) -> dict:
    """Mann-Kendall trend test (normal approximation, tie-corrected)."""
    n = len(ys)
    if n < 4:
        return {"S": 0, "z": 0.0, "p": 1.0}
    s = 0
    for i in range(n - 1):
        for j in range(i + 1, n):
            s += (ys[j] > ys[i]) - (ys[j] < ys[i])
    ties: dict = {}
    for y in ys:
        ties[y] = ties.get(y, 0) + 1
    var = (n * (n - 1) * (2 * n + 5) - sum(t * (t - 1) * (2 * t + 5) for t in ties.values())) / 18.0
    if var <= 0:
        return {"S": s, "z": 0.0, "p": 1.0}
    z = (s - 1) / math.sqrt(var) if s > 0 else ((s + 1) / math.sqrt(var) if s < 0 else 0.0)
    p = math.erfc(abs(z) / math.sqrt(2))  # two-sided
    return {"S": s, "z": z, "p": p}
