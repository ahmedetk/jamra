"""Build everything the website needs from the downloaded FIRMS archive.

Steps: aggregate -> quality checks (inventory, outages, ratio drift) ->
harmonization (M0-M5, leave-one-year-out CV, choice) -> NOAA-20 -> S-NPP factor
-> FRP stability test -> calendar colour agreement -> harmonized series for
countries, presets and grid cells -> web data files + model_report.json.

Usage: python -m jamra.build
Code written with the help of an SI coding assistant (Claude Code).
"""
from __future__ import annotations

import json
import math
import time
from datetime import date, datetime, timedelta, timezone
from statistics import median

from . import aggregate, anomaly, config, harmonize, validate
from .firms import SENSOR_NAMES, month_index, month_label

START_MI = month_index(2003, 1)
SNPP_FIRST_FULL_MI = month_index(2012, 2)  # S-NPP data start 2012-01-20
NOAA20_FIRST_FULL_MI = month_index(2018, 5)  # NOAA-20 data start 2018-04-01 (first months sparse)


def rnd(x, nd=1):
    return None if x is None else round(x, nd)


def build() -> dict:
    t0 = time.time()
    cfg = config.load()
    acfg = cfg["anomaly"]
    hcfg = cfg["harmonization"]
    agg = aggregate.build()
    print(f"aggregated in {time.time() - t0:.0f}s; cells={len(agg.cells)} flagged={len(agg.flagged_cells)}")

    countries = list(cfg["countries"].keys())
    presets = cfg["presets"]
    last_day = date.fromordinal(max(agg.last_day.values()))
    end_mi = month_index(last_day.year, last_day.month)
    months = list(range(START_MI, end_mi + 1))

    def mser(area, sensor, static=False, frp=False):
        src = agg.monthly_static if static else agg.monthly
        d = src[area][sensor]
        return [d[mi][1 if frp else 0] if mi in d else 0 for mi in months]

    def sensor_valid(sensor, mi):
        first = {"A": month_index(2002, 7), "T": START_MI, "N": SNPP_FIRST_FULL_MI, "J": NOAA20_FIRST_FULL_MI}[sensor]
        last = month_index(date.fromordinal(agg.last_day[sensor]).year, date.fromordinal(agg.last_day[sensor]).month)
        return first <= mi <= last

    # ------------------------------------------------ region totals + outages
    reg = {s: [sum(mser(c, s)[i] for c in countries) for i in range(len(months))] for s in "ATNJ"}
    overlap_idx = [i for i, mi in enumerate(months) if sensor_valid("A", mi) and sensor_valid("N", mi)]
    med_ratio = median(reg["N"][i] / reg["A"][i] for i in overlap_idx if reg["A"][i] >= 30)
    outages = []
    for i, mi in enumerate(months):
        a, n, j = reg["A"][i], reg["N"][i], reg["J"][i]
        if sensor_valid("A", mi) and sensor_valid("N", mi):
            if a >= 30 and n < 0.15 * med_ratio * a:
                outages.append({"month": month_label(mi), "sensor": "N", "MODIS_A": a, "VIIRS_N": n})
            elif n >= 100 and a < 0.15 * n / med_ratio:
                outages.append({"month": month_label(mi), "sensor": "A", "MODIS_A": a, "VIIRS_N": n})
        if sensor_valid("J", mi) and sensor_valid("N", mi) and n >= 100 and j < 0.15 * n:
            outages.append({"month": month_label(mi), "sensor": "J", "VIIRS_N": n, "VIIRS_J": j})
    out_set = {(o["month"], o["sensor"]) for o in outages}

    # ------------------------------------------------ year-by-year ratio drift
    drift = []
    for y in range(2012, date.fromordinal(agg.last_day["N"]).year + 1):
        idx = [i for i, mi in enumerate(months) if mi // 12 + 2000 == y and i in set(overlap_idx)
               and (month_label(mi), "N") not in out_set and (month_label(mi), "A") not in out_set]
        sa = sum(reg["A"][i] for i in idx)
        sn = sum(reg["N"][i] for i in idx)
        st = sum(reg["T"][i] for i in idx)
        sj = sum(reg["J"][i] for i in idx if sensor_valid("J", months[i]))
        sn_j = sum(reg["N"][i] for i in idx if sensor_valid("J", months[i]))
        per_country = {}
        for c in countries:
            ca = sum(mser(c, "A")[i] for i in idx)
            cn = sum(mser(c, "N")[i] for i in idx)
            per_country[c] = rnd(cn / ca, 3) if ca else None
        drift.append({"year": y, "months": len(idx), "MODIS_Aqua": sa, "VIIRS_SNPP": sn, "MODIS_Terra": st,
                      "ratio_N_over_A": rnd(sn / sa, 3) if sa else None,
                      "ratio_T_over_A": rnd(st / sa, 3) if sa else None,
                      "ratio_J_over_N": rnd(sj / sn_j, 3) if sn_j else None,
                      "per_country_N_over_A": per_country})
    ratios = [d["ratio_N_over_A"] for d in drift if d["ratio_N_over_A"] and d["months"] >= 10
              and (d["year"] < last_day.year or last_day.month == 12)]
    ref = median(ratios)
    tol = 0.15
    if hcfg["calibration_years"] == "auto":
        full_until = last_day.year if last_day.month == 12 else last_day.year - 1
        cal_years = [d["year"] for d in drift if d["ratio_N_over_A"] and d["months"] >= 10
                     and d["year"] <= full_until and abs(d["ratio_N_over_A"] / ref - 1) <= tol]
    else:
        cal_years = list(hcfg["calibration_years"])
    for d in drift:
        d["used_for_calibration"] = d["year"] in cal_years

    # ------------------------------------------------ harmonization CV
    def cal_rows(m_sensor="A", v_sensor="N", years=None, min_mi=SNPP_FIRST_FULL_MI):
        rows = []
        for c in countries:
            M = mser(c, m_sensor)
            V = mser(c, v_sensor)
            for i, mi in enumerate(months):
                y = mi // 12 + 2000
                if years is not None and y not in years:
                    continue
                if mi < min_mi or not (sensor_valid(m_sensor, mi) and sensor_valid(v_sensor, mi)):
                    continue
                if (month_label(mi), m_sensor) in out_set or (month_label(mi), v_sensor) in out_set:
                    continue
                rows.append({"country": c, "month": mi % 12 + 1, "year": y, "M": M[i], "V": V[i]})
        return rows

    rows = cal_rows(years=set(cal_years))
    models = ["M0", "M1", "M2", "M3", "M4", "M5"]
    cv = harmonize.loyo(rows, models, hcfg["lambdas"])
    cvm = cv["metrics"]
    chosen, why = harmonize.choose_model({m: cvm[m] for m in models if m != "M0"}, hcfg["choose_within"])
    lam = harmonize.choose_lambda(rows, hcfg["lambdas"])

    # ---------------- independent test on held-out years (validate.py)
    test_years = [y for y in hcfg.get("test_years", []) if y in cal_years]
    dev_years = [y for y in cal_years if y not in test_years]
    ok_idx = {i for i, mi in enumerate(months) if mi >= SNPP_FIRST_FULL_MI
              and (month_label(mi), "N") not in out_set and (month_label(mi), "A") not in out_set}
    region_sets = {"presets": [], "grid_1deg": []}
    for p, spec in presets.items():
        region_sets["presets"] += validate.region_rows(mser(p, "A"), mser(p, "N"), months, set(cal_years), ok_idx,
                                                       spec["country"], p)
    owner_tmp = aggregate.cell_owner(agg)
    boxes: dict = {}
    pos = {mi: i for i, mi in enumerate(months)}
    for cid, by_s in agg.cells.items():
        if cid in agg.flagged_cells:
            continue
        ix, iy = (int(v) for v in cid.split("_"))
        b = boxes.setdefault(f"{ix // 10}_{iy // 10}", {"A": [0] * len(months), "N": [0] * len(months), "own": {}})
        for s in ("A", "N"):
            for mi, n in by_s.get(s, {}).items():
                if mi in pos:
                    b[s][pos[mi]] += n
        o = owner_tmp[cid]
        b["own"][o] = b["own"].get(o, 0) + sum(by_s.get("N", {}).values())
    for bid, b in boxes.items():
        total_v = sum(b["N"][i] for i in ok_idx if months[i] // 12 + 2000 in cal_years)
        if total_v >= 100 and b["own"]:
            ctry = max(b["own"].items(), key=lambda kv: kv[1])[0]
            region_sets["grid_1deg"] += validate.region_rows(b["A"], b["N"], months, set(cal_years), ok_idx, ctry, bid)
    validation = validate.run([dict(r) for r in rows], region_sets, dev_years, test_years, models, hcfg["lambdas"],
                              acfg, hcfg["choose_within"]) if test_years else None
    if validation:
        chosen = validation["chosen_model_dev"]
        why = validation["choice_reason_dev"] + " (chosen on development years only)"
        area_method = "local" if validation["decision"]["adopt_local_factor"] else "baseline"
        lam_area = validation["lambda_area"]
        print("validation:", validation["decision"]["text"])
    else:
        area_method, lam_area = "local", lam
    unc_small = (validation["small_regions"]["presets"][area_method]["mdape"] if validation else None)
    final = harmonize.fit(chosen, rows, lam)
    m2 = harmonize.fit("M2", rows)
    m3 = harmonize.fit("M3", rows, lam)
    k_global = m2["k"]
    unc_month = cvm[chosen]["monthly"]["mdape"]
    unc_year = cvm[chosen]["annual"]["mdape"]
    if validation:  # use the stricter held-out test-year errors for the ± shown to users
        unc_month = validation["test_countries"][chosen]["mdape"]
        unc_year = validation["test_countries"][chosen]["annual"]["mdape"]
    print(f"calibration years {cal_years}; chosen {chosen}; lam={lam}; k_global={k_global:.2f}")

    # alternative pairing: Terra + Aqua (could extend the record to 2001)
    rows_ta = []
    for c in countries:
        A, T, V = mser(c, "A"), mser(c, "T"), mser(c, "N")
        for i, mi in enumerate(months):
            y = mi // 12 + 2000
            if y in cal_years and mi >= SNPP_FIRST_FULL_MI and (month_label(mi), "N") not in out_set \
                    and (month_label(mi), "A") not in out_set:
                rows_ta.append({"country": c, "month": mi % 12 + 1, "year": y, "M": A[i] + T[i], "V": V[i]})
    cv_ta = harmonize.loyo(rows_ta, [chosen if chosen != "M3" else "M3"], hcfg["lambdas"])["metrics"]

    # ------------------------------------------------ NOAA-20 -> S-NPP factor (for live data)
    rows_jn = cal_rows("J", "N", years=None, min_mi=NOAA20_FIRST_FULL_MI)
    cv_jn = harmonize.loyo(rows_jn, ["M0", "M1", "M2"], hcfg["lambdas"])["metrics"]
    jn_choice, jn_why = harmonize.choose_model({m: cv_jn[m] for m in ("M1", "M2")}, hcfg["choose_within"])
    jn = harmonize.fit(jn_choice, rows_jn)
    k_jn_c = {c: (jn["k_c"].get(c, jn["k"]) if jn_choice == "M2" else jn["k"]) for c in countries}

    # ------------------------------------------------ FRP stability test
    frp_rows = []
    for c in countries:
        A, V = mser(c, "A"), mser(c, "N")
        Af, Vf = mser(c, "A", frp=True), mser(c, "N", frp=True)
        for i, mi in enumerate(months):
            y = mi // 12 + 2000
            if y in cal_years and mi >= SNPP_FIRST_FULL_MI and A[i] >= 10 and Af[i] > 0:
                frp_rows.append({"country": c, "count_ratio": V[i] / A[i], "frp_ratio": Vf[i] / Af[i]})

    def cv_of(xs):
        if len(xs) < 3:
            return None
        mu = sum(xs) / len(xs)
        sd = math.sqrt(sum((x - mu) ** 2 for x in xs) / (len(xs) - 1))
        return sd / mu if mu else None

    frp_by_c = {}
    for c in countries:
        rc = [r["count_ratio"] for r in frp_rows if r["country"] == c]
        rf = [r["frp_ratio"] for r in frp_rows if r["country"] == c]
        if len(rc) >= 6:
            frp_by_c[c] = {"months": len(rc), "cv_count_ratio": rnd(cv_of(rc), 3), "cv_frp_ratio": rnd(cv_of(rf), 3),
                           "median_count_ratio": rnd(median(rc), 3), "median_frp_ratio": rnd(median(rf), 3)}
    pooled_c = cv_of([r["count_ratio"] for r in frp_rows])
    pooled_f = cv_of([r["frp_ratio"] for r in frp_rows])
    frp_wins = sum(1 for v in frp_by_c.values() if v["cv_frp_ratio"] is not None and v["cv_frp_ratio"] < v["cv_count_ratio"])
    frp_validated = pooled_f is not None and pooled_c is not None and pooled_f < pooled_c and frp_wins > len(frp_by_c) / 2
    frp_test = {"hypothesis": "Summed FRP is more stable between sensors than counts.",
                "pooled_cv_count_ratio": rnd(pooled_c, 3), "pooled_cv_frp_ratio": rnd(pooled_f, 3),
                "countries_where_frp_more_stable": frp_wins, "countries_tested": len(frp_by_c),
                "validated": frp_validated, "by_country": frp_by_c,
                "rule": "FRP is offered as a calendar metric only if the VIIRS/MODIS FRP ratio varies less "
                        "(lower coefficient of variation) than the count ratio, pooled and in most countries."}

    # ------------------------------------------------ calendar colour agreement (out-of-fold)
    oof = cv["oof"][chosen]
    actual = {(r["country"], r["year"], r["month"]): r["V"] for r in oof}
    agree = total = 0
    confusion: dict = {}
    by_c_agree: dict = {}
    busy = [0, 0]
    for r in oof:
        others = [actual[(r["country"], y, r["month"])] for y in cal_years
                  if y != r["year"] and (r["country"], y, r["month"]) in actual]
        c_pred = anomaly.category(r["P"], others, acfg)
        c_act = anomaly.category(r["V"], others, acfg)
        if c_pred and c_act:
            total += 1
            agree += c_pred == c_act
            confusion[f"{c_act}->{c_pred}"] = confusion.get(f"{c_act}->{c_pred}", 0) + 1
            bc = by_c_agree.setdefault(r["country"], [0, 0])
            bc[0] += c_pred == c_act
            bc[1] += 1
            if median(others) >= 30:
                busy[0] += c_pred == c_act
                busy[1] += 1
    m0_agree = m0_total = 0
    for r in cv["oof"]["M0"]:
        others = [actual[(r["country"], y, r["month"])] for y in cal_years
                  if y != r["year"] and (r["country"], y, r["month"]) in actual]
        c_pred = anomaly.category(r["P"], others, acfg)
        c_act = anomaly.category(r["V"], others, acfg)
        if c_pred and c_act:
            m0_total += 1
            m0_agree += c_pred == c_act
    color_agreement = {"model": chosen, "months": total, "same_colour_pct": rnd(100 * agree / total, 1) if total else None,
                       "without_harmonization_pct": rnd(100 * m0_agree / m0_total, 1) if m0_total else None,
                       "busy_months_pct": rnd(100 * busy[0] / busy[1], 1) if busy[1] else None,
                       "busy_months": busy[1],
                       "busy_rule": "months whose usual (median of other years) is at least 30 hotspots",
                       "by_country_pct": {c: rnd(100 * a / n, 1) for c, (a, n) in by_c_agree.items()},
                       "confusion": confusion}

    # ------------------------------------------------ harmonized series per area
    def factor_for(area_country: str, month: int) -> float:
        if chosen == "M3":
            return final["k_cm"].get((area_country, month), final["k_c"].get(area_country, final["k"]))
        if chosen == "M2":
            return final["k_c"].get(area_country, final["k"])
        if chosen == "M1":
            return final["k"]
        # M4/M5 are non-linear; use the monthly effective ratio from M3 for daily scaling
        return m3["k_cm"].get((area_country, month), m3["k_c"].get(area_country, m3["k"]))

    area_specs = []
    for c, spec in cfg["countries"].items():
        area_specs.append({"id": spec["id"], "label": spec["label"], "kind": "country", "country": c, "key": c})
    for p, spec in presets.items():
        area_specs.append({"id": p, "label": spec["label"], "kind": "preset", "country": spec["country"],
                           "key": p, "box": spec["box"]})

    cal_idx = [i for i, mi in enumerate(months) if mi // 12 + 2000 in cal_years and mi >= SNPP_FIRST_FULL_MI
               and (month_label(mi), "N") not in out_set and (month_label(mi), "A") not in out_set]
    day0 = date(2003, 1, 1)
    n_days = (last_day - day0).days + 1
    areas_out = {}
    for a in area_specs:
        key, ctry = a["key"], a["country"]
        A, T, N, J = (mser(key, s) for s in "ATNJ")
        As, Ns, Js = (mser(key, s, static=True) for s in "ANJ")
        Nf, Af = mser(key, "N", frp=True), mser(key, "A", frp=True)
        # area-specific factor (presets): own overlap ratio shrunk toward the country
        V_cal = sum(N[i] for i in cal_idx)
        M_cal = sum(A[i] for i in cal_idx)
        k_parent = m2["k_c"].get(ctry, k_global)
        yearly = []
        for y in cal_years:
            idx = [i for i in cal_idx if months[i] // 12 + 2000 == y]
            yearly.append((sum(N[i] for i in idx), sum(A[i] for i in idx)))
        if a["kind"] == "preset":
            if area_method == "local":
                k_area = harmonize.area_factor(V_cal, M_cal, k_parent, lam_area)
                w_own = M_cal / (M_cal + lam_area) if (M_cal + lam_area) else 0
            else:
                k_area, w_own = k_parent, 0.0
            se_rel = harmonize.ratio_uncertainty(yearly)
        else:
            k_area = k_parent
            w_own = 1.0
            se_rel = harmonize.ratio_uncertainty(yearly)
        harm, src, lo, hi, harm_static = [], [], [], [], []
        for i, mi in enumerate(months):
            month = mi % 12 + 1
            if mi < SNPP_FIRST_FULL_MI:
                if a["kind"] == "country":
                    h = harmonize.predict(final, ctry, month, A[i])
                    hs = harmonize.predict(final, ctry, month, A[i] + As[i]) - h
                else:
                    seasonal = factor_for(ctry, month) / k_parent if k_parent else 1.0
                    h = A[i] * k_area * seasonal
                    hs = As[i] * k_area * seasonal
                rel = (unc_small if (a["kind"] == "preset" and unc_small) else unc_month) or 0
                harm.append(rnd(h)); src.append("M"); lo.append(rnd(h * (1 - rel))); hi.append(rnd(h * (1 + rel)))
                harm_static.append(rnd(hs))
            elif (month_label(mi), "N") in out_set or not sensor_valid("N", mi):
                if sensor_valid("J", mi) and (month_label(mi), "J") not in out_set:
                    k = k_jn_c.get(ctry, jn["k"])
                    harm.append(rnd(J[i] * k)); src.append("J"); lo.append(None); hi.append(None)
                    harm_static.append(rnd(Js[i] * k))
                else:
                    harm.append(None); src.append("G"); lo.append(None); hi.append(None); harm_static.append(None)
            else:
                harm.append(N[i]); src.append("N"); lo.append(None); hi.append(None); harm_static.append(Ns[i])
        # daily harmonized (static cells already excluded)
        dA, dN, dJ = agg.daily[key]["A"], agg.daily[key]["N"], agg.daily[key]["J"]
        daily = []
        for k in range(n_days):
            d = day0 + timedelta(days=k)
            mi = month_index(d.year, d.month)
            o = d.toordinal()
            s = src[mi - START_MI]
            if s == "M":
                f = (factor_for(ctry, d.month) if a["kind"] == "country"
                     else k_area * factor_for(ctry, d.month) / k_parent if k_parent else k_area)
                daily.append(round(dA.get(o, 0) * f, 1))
            elif s == "N":
                daily.append(dN.get(o, 0))
            elif s == "J":
                daily.append(round(dJ.get(o, 0) * k_jn_c.get(ctry, jn["k"]), 1))
            else:
                daily.append(None)
        areas_out[a["id"]] = {
            **{k: v for k, v in a.items() if k != "key"},
            "start": month_label(months[0]),
            "series": {"A": A, "T": T, "N": [N[i] if sensor_valid("N", mi) else None for i, mi in enumerate(months)],
                       "J": [J[i] if sensor_valid("J", mi) else None for i, mi in enumerate(months)],
                       "A_frp": [rnd(x) for x in Af], "N_frp": [rnd(x) for x in Nf]},
            "harm": harm, "src": src, "lo": lo, "hi": hi, "harm_static": harm_static,
            "factor": {"k": rnd(k_area, 3), "k_country": rnd(k_parent, 3), "own_weight": rnd(w_own, 2),
                       "rel_se": rnd(se_rel, 3), "V_overlap": V_cal, "M_overlap": M_cal},
            "daily_start": day0.isoformat(), "daily": daily,
        }

    # ------------------------------------------------ grid cells for custom polygons
    owner = aggregate.cell_owner(agg)
    cells_out = {}
    for cid, by_s in agg.cells.items():
        entry = {"c": owner[cid]}
        for s in "ANJ":
            ms = by_s.get(s)
            if ms:
                flat = []
                for mi in sorted(ms):
                    if mi >= START_MI:
                        flat += [mi - START_MI, ms[mi]]
                if flat:
                    entry[s] = flat
        cells_out[cid] = entry

    # ------------------------------------------------ season start trends (countries)
    season = {}
    for a in area_specs:
        h = areas_out[a["id"]]["harm"]
        yrs, starts = [], []
        for y in range(2003, last_day.year + (1 if last_day.month == 12 else 0)):
            i0 = month_index(y, 1) - START_MI
            vals = h[i0:i0 + 12]
            if len(vals) == 12 and all(v is not None for v in vals):
                s = anomaly.season_start(vals)
                if s:
                    yrs.append(y)
                    starts.append(s)
        mk = anomaly.mann_kendall(starts)
        season[a["id"]] = {"years": yrs, "start_month": starts,
                           "theil_sen_months_per_decade": rnd((anomaly.theil_sen(yrs, starts) or 0) * 10, 2),
                           "mann_kendall_p": rnd(mk["p"], 3), "significant": mk["p"] < 0.05}

    # ------------------------------------------------ inventory
    inventory = []
    for c in countries:
        for s in "ATNJ":
            for y, reasons in sorted(agg.removed[c][s].items()):
                inventory.append({"country": c, "sensor": s, "year": y, **dict(reasons)})

    report = {
        "generated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "data_through": last_day.isoformat(),
        "sensors": SENSOR_NAMES,
        "unit": "hotspots (satellite fire pixels), not fires",
        "filters": cfg["filters"],
        "calibration": {"pair": "MODIS Aqua -> VIIRS S-NPP", "years": cal_years,
                        "rule": f"Overlap years whose region-wide S-NPP/Aqua ratio is within ±{tol:.0%} of the "
                                f"median year ratio ({ref:.2f}); outage months excluded.",
                        "months_used": len(rows)},
        "drift": drift,
        "outages": outages,
        "viirs_vs_modis_ratio": rnd(k_global, 2),
        "cv": {m: cvm[m] for m in models},
        "model_labels": harmonize.MODEL_LABELS,
        "chosen_model": chosen, "choice_reason": why, "lambda": lam,
        "validation": validation, "area_method": area_method, "lambda_area": lam_area,
        "uncertainty_small_regions": rnd(unc_small, 3),
        "lambda_per_fold": cv["lambda_per_fold"],
        "factors": {"global": rnd(k_global, 3), "by_country": {c: rnd(v, 3) for c, v in m2["k_c"].items()},
                    "by_country_month": {f"{c}|{m}": rnd(v, 3) for (c, m), v in m3["k_cm"].items()}},
        "uncertainty": {"monthly_rel": rnd(unc_month, 3), "annual_rel": rnd(unc_year, 3),
                        "small_regions_rel": rnd(unc_small, 3),
                        "how": "Median absolute % error on the held-out test years (countries; small regions "
                               "separately), for months with at least 10 actual VIIRS hotspots."},
        "terra_aqua_alternative": {"model": chosen, "cv": cv_ta.get(chosen),
                                   "note": "Same model using Terra+Aqua MODIS instead of Aqua only."},
        "noaa20_to_snpp": {"choice": jn_choice, "why": jn_why, "global": rnd(jn["k"], 3),
                           "by_country": {c: rnd(v, 3) for c, v in k_jn_c.items()}, "cv": cv_jn,
                           "months_used": len(rows_jn)},
        "frp_test": frp_test,
        "colour_agreement": color_agreement,
        "season_start": season,
        "persistence_filter": {"flagged_cells": len(agg.flagged_cells), "spec": cfg["filters"]["persistence"]},
        "inventory": inventory,
        "scatter": [{"c": r["country"], "y": r["year"], "m": r["month"], "M": r["M"], "V": r["V"],
                     "P0": r["M"], "P": rnd(r["P"])} for r in oof],
    }
    meta = {
        "product": cfg["product"],
        "generated_utc": report["generated_utc"],
        "data_through": last_day.isoformat(),
        "start": month_label(months[0]), "n_months": len(months),
        "snpp_switch": month_label(SNPP_FIRST_FULL_MI),
        "areas": [{k: v for k, v in a.items() if k != "key"} for a in area_specs],
        "chosen_model": chosen, "uncertainty_monthly": rnd(unc_month, 3),
        "viirs_vs_modis_ratio": rnd(k_global, 2),
        "lambda": lam, "k_global": rnd(k_global, 3),
        "k_by_country": {cfg["countries"][c]["id"]: rnd(v, 3) for c, v in m2["k_c"].items()},
        "k_jn_by_country": {cfg["countries"][c]["id"]: rnd(v, 3) for c, v in k_jn_c.items()},
        "anomaly": acfg, "cell_deg": cfg["grid"]["cell_deg"],
        "frp_validated": frp_validated,
        "area_method": area_method, "lambda_area": lam_area, "uncertainty_small": rnd(unc_small, 3),
    }
    return {"report": report, "meta": meta, "areas": areas_out, "cells": cells_out,
            "flagged": sorted(agg.flagged_cells)}


def write(out: dict) -> None:
    processed = config.path("processed")
    web = config.path("web_data")
    (web / "areas").mkdir(parents=True, exist_ok=True)
    processed.mkdir(parents=True, exist_ok=True)
    dump = lambda obj: json.dumps(obj, separators=(",", ":"), ensure_ascii=False)
    (processed / "model_report.json").write_text(json.dumps(out["report"], indent=1, ensure_ascii=False), encoding="utf-8")
    (web / "model_report.json").write_text(dump(out["report"]), encoding="utf-8")
    (web / "meta.json").write_text(dump(out["meta"]), encoding="utf-8")
    for aid, a in out["areas"].items():
        (web / "areas" / f"{aid}.json").write_text(dump(a), encoding="utf-8")
    (web / "cells.json").write_text(dump({"start": out["meta"]["start"], "cell_deg": out["meta"]["cell_deg"],
                                          "cells": out["cells"], "flagged": out["flagged"]}), encoding="utf-8")


def main() -> None:
    out = build()
    write(out)
    r = out["report"]
    print(json.dumps({k: r[k] for k in ("chosen_model", "choice_reason", "viirs_vs_modis_ratio", "uncertainty",
                                        "colour_agreement")}, indent=1)[:2500])


if __name__ == "__main__":
    main()
