"""MODIS -> VIIRS harmonization models and leave-one-year-out cross-validation.

Unit of analysis: monthly hotspot counts per country. Pair: Aqua MODIS (M)
vs S-NPP VIIRS (V); both cross the equator around 1:30 pm / 1:30 am.

Models (see the website's "Why not just...?" box):
  M0 no harmonization        pred = M
  M1 one global ratio        pred = k * M,          k = sum V / sum M
  M2 ratio per country       pred = k_c * M
  M3 country x month ratio   k_cm = (V_cm + lam * k_c) / (M_cm + lam)  (shrinkage)
  M4 log-log regression per country, with Duan smearing
  M5 empirical quantile mapping per country

Code written with the help of an AI coding assistant (Claude Code by Anthropic).
"""
from __future__ import annotations

import math
from statistics import median

COMPLEXITY_ORDER = ["M1", "M2", "M4", "M3", "M5"]  # fewest parameters first
MODEL_LABELS = {
    "M0": "No harmonization",
    "M1": "One global ratio",
    "M2": "Ratio per country",
    "M3": "Ratio per country and month (shrinkage)",
    "M4": "Log-log regression per country",
    "M5": "Quantile mapping per country",
}


# --------------------------------------------------------------- fitting
def _ratio(v: float, m: float, fallback: float = 1.0) -> float:
    return v / m if m > 0 else fallback


def fit(model: str, train: list[dict], lam: float = 50.0) -> dict:
    """Fit a model. Rows: {country, month, year, M, V}."""
    gV = sum(r["V"] for r in train)
    gM = sum(r["M"] for r in train)
    k_global = _ratio(gV, gM)
    if model in ("M0",):
        return {"model": model}
    if model == "M1":
        return {"model": model, "k": k_global}
    by_c: dict = {}
    for r in train:
        a = by_c.setdefault(r["country"], [0.0, 0.0])
        a[0] += r["V"]
        a[1] += r["M"]
    k_c = {c: _ratio(v, m, k_global) for c, (v, m) in by_c.items()}
    if model == "M2":
        return {"model": model, "k_c": k_c, "k": k_global}
    if model == "M3":
        by_cm: dict = {}
        for r in train:
            a = by_cm.setdefault((r["country"], r["month"]), [0.0, 0.0])
            a[0] += r["V"]
            a[1] += r["M"]
        k_cm = {key: (v + lam * k_c.get(key[0], k_global)) / (m + lam) if (m + lam) > 0 else k_c.get(key[0], k_global)
                for key, (v, m) in by_cm.items()}
        return {"model": model, "k_cm": k_cm, "k_c": k_c, "k": k_global, "lam": lam}
    if model == "M4":
        params = {}
        for c in by_c:
            pts = [(math.log1p(r["M"]), math.log1p(r["V"])) for r in train if r["country"] == c]
            params[c] = _ols(pts)
        return {"model": model, "params": params, "k_c": k_c, "k": k_global}
    if model == "M5":
        dist = {}
        for c in by_c:
            ms = sorted(r["M"] for r in train if r["country"] == c)
            vs = sorted(r["V"] for r in train if r["country"] == c)
            dist[c] = (ms, vs)
        return {"model": model, "dist": dist, "k_c": k_c, "k": k_global}
    raise ValueError(model)


def _ols(pts: list[tuple[float, float]]) -> tuple[float, float, float] | None:
    n = len(pts)
    if n < 3:
        return None
    mx = sum(p[0] for p in pts) / n
    my = sum(p[1] for p in pts) / n
    sxx = sum((p[0] - mx) ** 2 for p in pts)
    if sxx == 0:
        return None
    b = sum((p[0] - mx) * (p[1] - my) for p in pts) / sxx
    a = my - b * mx
    smear = sum(math.exp(p[1] - (a + b * p[0])) for p in pts) / n  # Duan smearing
    return a, b, smear


def _ecdf_mid(sorted_xs: list[float], x: float) -> float:
    n = len(sorted_xs)
    below = sum(1 for v in sorted_xs if v < x)
    equal = sum(1 for v in sorted_xs if v == x)
    return (below + 0.5 * equal) / n


def _quantile_sorted(xs: list[float], p: float) -> float:
    if not xs:
        return 0.0
    pos = min(max(p, 0.0), 1.0) * (len(xs) - 1)
    lo, hi = math.floor(pos), math.ceil(pos)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def predict(params: dict, country: str, month: int, M: float) -> float:
    model = params["model"]
    if model == "M0":
        return M
    if model == "M1":
        return params["k"] * M
    if model == "M2":
        return params["k_c"].get(country, params["k"]) * M
    if model == "M3":
        k = params["k_cm"].get((country, month), params["k_c"].get(country, params["k"]))
        return k * M
    if model == "M4":
        p = params["params"].get(country)
        if p is None:
            return params["k_c"].get(country, params["k"]) * M
        a, b, smear = p
        return max(math.exp(a + b * math.log1p(M)) * smear - 1.0, 0.0)
    if model == "M5":
        d = params["dist"].get(country)
        if not d or not d[0]:
            return params["k_c"].get(country, params["k"]) * M
        ms, vs = d
        if M > ms[-1]:  # beyond the training range: extend with the country ratio
            return _quantile_sorted(vs, 1.0) * (M / ms[-1]) if ms[-1] > 0 else params["k_c"].get(country, params["k"]) * M
        return _quantile_sorted(vs, _ecdf_mid(ms, M))
    raise ValueError(model)


# ------------------------------------------------------------ evaluation
def metrics(pairs: list[tuple[float, float]]) -> dict:
    """pairs = [(predicted, actual)]."""
    if not pairs:
        return {}
    mae = sum(abs(p - a) for p, a in pairs) / len(pairs)
    big = [abs(p - a) / a for p, a in pairs if a >= 10]
    mdape = median(big) if big else None
    sa = sum(a for _, a in pairs)
    bias = (sum(p for p, _ in pairs) - sa) / sa if sa else None
    lp = [math.log1p(max(p, 0.0)) for p, _ in pairs]
    la = [math.log1p(a) for _, a in pairs]
    return {"mae": mae, "mdape": mdape, "bias": bias, "r_log": _pearson(lp, la), "n": len(pairs)}


def _pearson(x: list[float], y: list[float]) -> float | None:
    n = len(x)
    if n < 3:
        return None
    mx, my = sum(x) / n, sum(y) / n
    sxy = sum((a - mx) * (b - my) for a, b in zip(x, y))
    sxx = sum((a - mx) ** 2 for a in x)
    syy = sum((b - my) ** 2 for b in y)
    return sxy / math.sqrt(sxx * syy) if sxx > 0 and syy > 0 else None


def choose_lambda(rows: list[dict], lambdas: list[float]) -> float:
    """Pick lambda for M3 by leave-one-year-out MAE on the given rows."""
    years = sorted({r["year"] for r in rows})
    best = None
    for lam in lambdas:
        err, n = 0.0, 0
        for y in years:
            train = [r for r in rows if r["year"] != y]
            test = [r for r in rows if r["year"] == y]
            p = fit("M3", train, lam)
            for r in test:
                err += abs(predict(p, r["country"], r["month"], r["M"]) - r["V"])
                n += 1
        mae = err / max(n, 1)
        if best is None or mae < best[1]:
            best = (lam, mae)
    return best[0]


def loyo(rows: list[dict], models: list[str], lambdas: list[float]) -> dict:
    """Leave-one-year-out CV. Returns per-model metrics and out-of-fold predictions."""
    years = sorted({r["year"] for r in rows})
    oof: dict = {m: [] for m in models}
    lam_used: list = []
    for y in years:
        train = [r for r in rows if r["year"] != y]
        test = [r for r in rows if r["year"] == y]
        for m in models:
            lam = 0.0
            if m == "M3":
                lam = choose_lambda(train, lambdas)  # nested: tuned without the held-out year
                lam_used.append(lam)
            p = fit(m, train, lam)
            for r in test:
                oof[m].append({**r, "P": predict(p, r["country"], r["month"], r["M"])})
    result = {}
    for m in models:
        monthly = metrics([(r["P"], r["V"]) for r in oof[m]])
        annual_tot: dict = {}
        for r in oof[m]:
            a = annual_tot.setdefault((r["country"], r["year"]), [0.0, 0.0])
            a[0] += r["P"]
            a[1] += r["V"]
        annual = metrics([tuple(v) for v in annual_tot.values()])
        result[m] = {"monthly": monthly, "annual": annual}
    return {"metrics": result, "oof": oof, "lambda_per_fold": lam_used}


def choose_model(cv_metrics: dict, within: float = 0.05) -> tuple[str, str]:
    cands = [m for m in COMPLEXITY_ORDER if m in cv_metrics]
    best_mae = min(cv_metrics[m]["monthly"]["mae"] for m in cands)
    best_model = min(cands, key=lambda m: cv_metrics[m]["monthly"]["mae"])
    for m in cands:
        if cv_metrics[m]["monthly"]["mae"] <= best_mae * (1 + within):
            why = (f"{m} ({MODEL_LABELS[m]}) is the simplest model whose cross-validated MAE "
                   f"({cv_metrics[m]['monthly']['mae']:.1f}) is within {within:.0%} of the best "
                   f"({best_model}: {best_mae:.1f}).")
            return m, why
    return best_model, "best MAE"


def area_factor(V: float, M: float, k_parent: float, lam: float) -> float:
    """Hierarchical shrinkage: an area's own ratio, pulled toward its parent's ratio
    when the area has few hotspots. Plain words: few fires -> lean on the country."""
    return (V + lam * k_parent) / (M + lam) if (M + lam) > 0 else k_parent


def ratio_uncertainty(yearly: list[tuple[float, float]]) -> float | None:
    """Relative standard error of a pooled ratio from year-to-year variation."""
    rs = [v / m for v, m in yearly if m > 0]
    if len(rs) < 3:
        return None
    mean = sum(rs) / len(rs)
    sd = math.sqrt(sum((r - mean) ** 2 for r in rs) / (len(rs) - 1))
    return (sd / math.sqrt(len(rs))) / mean if mean > 0 else None
