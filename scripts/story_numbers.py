"""Compute every number used in the slides from pipeline outputs (single source of truth).

Writes data/processed/slide_numbers.json. scripts/check_numbers.py verifies that
the slides contain exactly these numbers. Written with an SI coding assistant (Claude Code).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "pipeline"))
from jamra import anomaly  # noqa: E402

WEB = ROOT / "web" / "public" / "data"
MONTHS = ["January", "February", "March", "April", "May", "June", "July", "August",
          "September", "October", "November", "December"]


def load(name):
    return json.loads((WEB / name).read_text(encoding="utf-8"))


def month_story(area_id, year, month, report, from_y=2003, to_y=2025):
    a = load(f"areas/{area_id}.json")
    y0 = int(a["start"][:4])
    idx = lambda y: (y - y0) * 12 + (month - 1)
    v = a["harm"][idx(year)]
    others = [a["harm"][idx(y)] for y in range(from_y, to_y + 1) if y != year and a["harm"][idx(y)] is not None]
    b = anomaly.baseline(others)
    pr = anomaly.percentile_rank(v, others)
    return {"area": a["label"], "area_id": area_id, "year": year, "month": MONTHS[month - 1], "value": round(v),
            "typical": int(b["median"] + 0.5), "times_typical": round(v / b["median"], 1) if b["median"] else None,
            "percentile": round(pr), "src": a["src"][idx(year)],
            "raw": a["series"]["A"][idx(year)] if year < 2012 else a["series"]["N"][idx(year)]}


def jump(area_id):
    a = load(f"areas/{area_id}.json")
    y0 = int(a["start"][:4])

    def yr(arr, y):
        i = (y - y0) * 12
        return sum(v for v in arr[i:i + 12] if v is not None)
    raw = {y: yr(a["series"]["A"], y) if y < 2012 else yr(a["series"]["N"], y) for y in range(2003, 2026)}
    harm = {y: yr(a["harm"], y) for y in range(2003, 2026)}
    m = lambda d, ys: sum(d[y] for y in ys) / len(ys)
    pre, post = range(2003, 2012), range(2012, 2026)
    return {"raw_ratio": round(m(raw, post) / m(raw, pre), 1), "harm_ratio": round(m(harm, post) / m(harm, pre), 1),
            "top_years": sorted(harm, key=harm.get, reverse=True)[:3]}


def main():
    r = load("model_report.json")
    cv = r["cv"]
    ch = r["chosen_model"]
    ca = r["colour_agreement"]
    out = {
        "k_global": round(r["viirs_vs_modis_ratio"], 1),
        "chosen_model": ch,
        "chosen_label": r["model_labels"][ch],
        "lambda": r["lambda"],
        "cal_years": r["calibration"]["years"],
        "n_cal_years": len(r["calibration"]["years"]),
        "excluded_years": [d["year"] for d in r["drift"] if d["months"] >= 10 and not d["used_for_calibration"]],
        "err_raw_month_pct": round(cv["M0"]["monthly"]["mdape"] * 100),
        "err_harm_month_pct": round(cv[ch]["monthly"]["mdape"] * 100),
        "err_raw_year_pct": round(cv["M0"]["annual"]["mdape"] * 100),
        "err_harm_year_pct": round(cv[ch]["annual"]["mdape"] * 100),
        "bias_raw_pct": round(cv["M0"]["monthly"]["bias"] * 100),
        "colour_agree_pct": round(ca["same_colour_pct"]),
        "colour_agree_raw_pct": round(ca["without_harmonization_pct"]),
        "colour_agree_busy_pct": round(ca["busy_months_pct"]),
        "colour_by_country": {k: round(v) for k, v in ca["by_country_pct"].items()},
        "frp_validated": r["frp_test"]["validated"],
        "frp_cv": r["frp_test"]["pooled_cv_frp_ratio"], "count_cv": r["frp_test"]["pooled_cv_count_ratio"],
        "k_jn": r["noaa20_to_snpp"]["global"],
        "uncertainty_month_pct": round(r["uncertainty"]["monthly_rel"] * 100),
        "uncertainty_year_pct": round(r["uncertainty"]["annual_rel"] * 100),
        "terra_aqua_mdape_pct": round(r["terra_aqua_alternative"]["cv"]["monthly"]["mdape"] * 100),
        "greece_jump": jump("greece"),
        "portugal_jump": jump("portugal"),
        "stories": {
            "greece_2007_08": month_story("greece", 2007, 8, r),
            "greece_2021_08": month_story("greece", 2021, 8, r),
            "greece_2023_08": month_story("greece", 2023, 8, r),
            "evia_2021_08": month_story("evia", 2021, 8, r),
            "portugal_2017_10": month_story("portugal", 2017, 10, r),
            "portugal_2017_06": month_story("portugal", 2017, 6, r),
        },
        "data_through": r["data_through"],
    }
    p = ROOT / "data" / "processed" / "slide_numbers.json"
    p.write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(out, indent=1, ensure_ascii=False))


if __name__ == "__main__":
    main()
