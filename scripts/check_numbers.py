"""Check that every number on the slides matches the pipeline outputs.

1. Recompute data/processed/slide_numbers.json from the website data (story_numbers.py).
2. Rebuild the expected strings and confirm each appears in slides/AstroByte_Slides.pptx.
Exit code 1 if anything is missing. Written with an SI coding assistant (Claude Code).
"""
import json
import subprocess
import sys
from pathlib import Path

from pptx import Presentation

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    subprocess.run([sys.executable, str(ROOT / "scripts" / "story_numbers.py")], check=True, capture_output=True)
    used = json.loads((ROOT / "slides" / "numbers_used.json").read_text(encoding="utf-8"))
    N = json.loads((ROOT / "data" / "processed" / "slide_numbers.json").read_text(encoding="utf-8"))
    prs = Presentation(str(ROOT / "slides" / "AstroByte_Slides.pptx"))
    text = []
    for slide in prs.slides:
        for shape in slide.shapes:
            if shape.has_text_frame:
                text.append(shape.text_frame.text)
        text.append(slide.notes_slide.notes_text_frame.text)
    blob = "\n".join(text)
    ev = N["stories"]["evia_2007_08"]
    T = N["test"]
    expected = {
        "k_global": f"{N['k_global']}×", "g_raw": f"{N['greece_jump']['raw_ratio']}×", "g_harm": f"{N['greece_jump']['harm_ratio']}×",
        "p_raw": f"{N['portugal_jump']['raw_ratio']}", "p_harm": f"{N['portugal_jump']['harm_ratio']}",
        "ncal": f"{N['n_cal_years']}", "chosen": N["chosen_model"],
        "ev07": f"August 2007, Evia: ≈ {ev['value']:,} hotspots", "ev07x": f"{ev['times_typical']}× a typical August",
        "unc": f"{N['unc_small_pct']}%",
        "err": f"{T['err_raw_pct']}% → {T['err_harm_pct']}%", "hits": f"{T['hits']} of {T['high_total']}",
        "small": f"{T['small_preset_pct']}%", "ta": f"{N['terra_aqua_mdape_pct']}% vs {N['cv_aqua_mdape_pct']}% error",
    }
    # the Arabic user guide must use the same numbers
    G = json.loads((ROOT / "report" / "numbers_used.json").read_text(encoding="utf-8"))
    guide_checks = {"hits": G["hits"] == T["hits"], "high_months": G["high_months"] == T["high_total"],
                    "test_err_harm": G["test_err_harm"] == f"{T['err_harm_pct']}%", "test_err_raw": G["test_err_raw"] == f"{T['err_raw_pct']}%",
                    "evia_2007_08": G["evia_2007_08"] == ev["value"], "k_global": G["k_global"] == N["k_global"]}
    for k, ok in guide_checks.items():
        print(f"{'OK ' if ok else 'BAD'} guide:{k}")
    bad = 0
    for k, exp in expected.items():
        got = used.get(k)
        ok = got == exp and exp in blob
        print(f"{'OK ' if ok else 'BAD'} {k:8s} expected '{exp}' slide '{got}'")
        bad += not ok
    bad += sum(1 for ok in guide_checks.values() if not ok)
    print("All slide and guide numbers match the data." if not bad else f"{bad} mismatches.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
