"""Independent test of the harmonization on held-out years.

Design
  * development years: model choice, lambda choice (leave-one-year-out inside them)
  * test years: never used in development; all reported test numbers come from here
Units
  * countries (monthly counts per country)
  * small regions: the preset fire areas, and every 1 x 1 degree box with enough hotspots
Methods for small regions
  * baseline: the country factor (chosen country model's month ratio) applied to the region
  * local factor: the region's own development-year ratio, shrunk toward the country
    ratio when it has few detections (area -> country -> global)
High-activity months
  * "Higher" or "Much higher" than usual, harmonized MODIS vs actual VIIRS: hits,
    misses, false alarms.

Code written with the help of an AI coding assistant (Claude Code by Anthropic).
"""
from __future__ import annotations

from statistics import median

from . import anomaly, harmonize

HIGH = {"higher", "much_higher"}


def region_rows(A: list, V: list, months: list, years: set, ok_idx: set, country: str, rid: str) -> list[dict]:
    rows = []
    for i, mi in enumerate(months):
        y = mi // 12 + 2000
        if y in years and i in ok_idx:
            rows.append({"region": rid, "country": country, "month": mi % 12 + 1, "year": y, "M": A[i], "V": V[i]})
    return rows


def ratio_factors(dev_rows: list[dict], lam: float) -> dict:
    """Country and country x month ratios fitted on development rows (M3-style)."""
    return harmonize.fit("M3", dev_rows, lam)


def country_month_factor(f: dict, country: str, month: int, seasonal: bool) -> float:
    kc = f["k_c"].get(country, f["k"])
    return f["k_cm"].get((country, month), kc) if seasonal else kc


def predict_region(method: str, r: dict, reg_dev: dict, f: dict, lam_a: float, seasonal: bool) -> float:
    kc = f["k_c"].get(r["country"], f["k"])
    k_month = country_month_factor(f, r["country"], r["month"], seasonal)
    if method == "baseline":
        return r["M"] * k_month
    v, m = reg_dev.get(r["region"], (0.0, 0.0))
    k_area = harmonize.area_factor(v, m, kc, lam_a)
    return r["M"] * k_area * (k_month / kc if kc else 1.0)


def dev_sums(rows: list[dict]) -> dict:
    out: dict = {}
    for r in rows:
        a = out.setdefault(r["region"], [0.0, 0.0])
        a[0] += r["V"]
        a[1] += r["M"]
    return {k: tuple(v) for k, v in out.items()}


def choose_area_lambda(dev_rows: list[dict], country_dev_rows: list[dict], lam: float, lambdas: list, seasonal: bool) -> float:
    years = sorted({r["year"] for r in dev_rows})
    best = None
    for la in lambdas:
        err = n = 0
        for y in years:
            f = ratio_factors([r for r in country_dev_rows if r["year"] != y], lam)
            sums = dev_sums([r for r in dev_rows if r["year"] != y])
            for r in dev_rows:
                if r["year"] == y:
                    err += abs(predict_region("local", r, sums, f, la, seasonal) - r["V"])
                    n += 1
        mae = err / max(n, 1)
        if best is None or mae < best[1]:
            best = (la, mae)
    return best[0]


def confusion(preds: list[dict], baseline_pool: dict, acfg: dict) -> dict:
    """preds: rows with P (predicted) and V (actual). baseline_pool[(region, month)] -> {year: actual}."""
    hits = misses = fa = cn = 0
    for r in preds:
        pool = baseline_pool.get((r["region"], r["month"]), {})
        others = [v for y, v in pool.items() if y != r["year"]]
        if len(others) < 5:
            continue
        a = anomaly.category(r["V"], others, acfg)
        p = anomaly.category(r["P"], others, acfg)
        if a is None or p is None:
            continue
        ah, ph = a in HIGH, p in HIGH
        hits += ah and ph
        misses += ah and not ph
        fa += ph and not ah
        cn += (not ah) and (not ph)
    return {"hits": hits, "misses": misses, "false_alarms": fa, "correct_negatives": cn,
            "hit_rate": round(hits / (hits + misses), 3) if hits + misses else None,
            "false_alarm_ratio": round(fa / (hits + fa), 3) if hits + fa else None,
            "false_alarm_rate": round(fa / (fa + cn), 3) if fa + cn else None}


def summarize(preds: list[dict]) -> dict:
    m = harmonize.metrics([(r["P"], r["V"]) for r in preds])
    return {k: (round(v, 3) if isinstance(v, float) else v) for k, v in m.items()}


def run(country_rows_all: list[dict], region_sets: dict, dev_years: list, test_years: list, models: list,
        lambdas: list, acfg: dict, within: float) -> dict:
    dev, test = set(dev_years), set(test_years)
    c_dev = [r for r in country_rows_all if r["year"] in dev]
    c_test = [r for r in country_rows_all if r["year"] in test]
    for r in country_rows_all:
        r.setdefault("region", r["country"])
    # 1) choose the country model on development years only
    cv_dev = harmonize.loyo(c_dev, models, lambdas)
    chosen, why = harmonize.choose_model({m: cv_dev["metrics"][m] for m in models if m != "M0"}, within)
    lam = harmonize.choose_lambda(c_dev, lambdas)
    test_country = {}
    country_preds = {}
    for m in models:
        p = harmonize.fit(m, c_dev, lam)
        preds = [{**r, "P": harmonize.predict(p, r["country"], r["month"], r["M"])} for r in c_test]
        country_preds[m] = preds
        test_country[m] = summarize(preds)
        ann: dict = {}
        for r in preds:
            a = ann.setdefault((r["country"], r["year"]), [0.0, 0.0])
            a[0] += r["P"]
            a[1] += r["V"]
        test_country[m]["annual"] = summarize([{"P": a, "V": b} for a, b in ann.values()])
    pool_c: dict = {}
    for r in country_rows_all:
        pool_c.setdefault((r["region"], r["month"]), {})[r["year"]] = r["V"]
    conf_country = {"raw_modis": confusion(country_preds["M0"], pool_c, acfg),
                    "harmonized": confusion(country_preds[chosen], pool_c, acfg)}
    # 2) small regions: baseline vs local factor
    seasonal = chosen in ("M3", "M4", "M5")
    f_dev = ratio_factors(c_dev, lam)
    small = {}
    all_reg_dev = [r for rs in region_sets.values() for r in rs if r["year"] in dev]
    lam_a = choose_area_lambda(all_reg_dev, c_dev, lam, lambdas, seasonal)
    for name, rows in region_sets.items():
        r_dev = [r for r in rows if r["year"] in dev]
        r_test = [r for r in rows if r["year"] in test]
        sums = dev_sums(r_dev)
        pool: dict = {}
        for r in rows:
            pool.setdefault((r["region"], r["month"]), {})[r["year"]] = r["V"]
        out = {"regions": len({r["region"] for r in rows}), "test_months": len(r_test)}
        for method in ("baseline", "local"):
            preds = [{**r, "P": predict_region(method, r, sums, f_dev, lam_a, seasonal)} for r in r_test]
            out[method] = summarize(preds)
            out[method]["confusion"] = confusion(preds, pool, acfg)
        raw = [{**r, "P": r["M"]} for r in r_test]
        out["raw_modis"] = summarize(raw)
        per_region = {}
        for rid in sorted({r["region"] for r in r_test}):
            sel = [r for r in r_test if r["region"] == rid]
            per_region[rid] = {meth: summarize([{**r, "P": predict_region(meth, r, sums, f_dev, lam_a, seasonal)} for r in sel])
                               for meth in ("baseline", "local")}
            per_region[rid]["actual_total"] = sum(r["V"] for r in sel)
        out["per_region"] = per_region
        small[name] = out
    # 3) decision: adopt the local factor only if the test years support it
    pooled = {meth: summarize([{**r, "P": predict_region(meth, r, dev_sums([x for x in rows if x["year"] in dev]), f_dev, lam_a, seasonal)}
                               for rows in region_sets.values() for r in rows if r["year"] in test])
              for meth in ("baseline", "local")}
    hr_b = [small[n]["baseline"]["confusion"]["hit_rate"] or 0 for n in small]
    hr_l = [small[n]["local"]["confusion"]["hit_rate"] or 0 for n in small]
    better_mae = pooled["local"]["mae"] < pooled["baseline"]["mae"]
    hits_ok = sum(hr_l) >= sum(hr_b) - 0.05 * len(hr_b)
    adopt = bool(better_mae and hits_ok)
    decision = {
        "adopt_local_factor": adopt,
        "rule": "Adopt the local factor only if, on the held-out test years, it lowers the small-region MAE "
                "and does not lower the hit rate for high-activity months by more than 5 points.",
        "pooled_small_regions": pooled,
        "text": ("The local factor was adopted: it lowered the small-region error on the test years."
                 if adopt else
                 "The local factor was NOT adopted: on the test years it did not beat the country factor, "
                 "so small areas use the country factor (baseline)."),
    }
    return {
        "dev_years": dev_years, "test_years": test_years,
        "split_rule": "The last four calibration years are held out as final test years; all model and lambda "
                      "choices use only the earlier development years.",
        "chosen_model_dev": chosen, "choice_reason_dev": why, "lambda_dev": lam, "lambda_area": lam_a,
        "cv_dev": {m: cv_dev["metrics"][m]["monthly"] for m in models},
        "test_countries": test_country,
        "confusion_countries": conf_country,
        "small_regions": small,
        "decision": decision,
        "high_rule": "A month is high-activity when it is 'Higher' or 'Much higher' than usual (percentile rank "
                     ">= 75 vs the same month in the other calibration years, with the small-count guard).",
    }
