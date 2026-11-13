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
    g07 = N["stories"]["greece_2007_08"]
    expected = {
        "k_global": f"{N['k_global']}×", "g_raw": f"{N['greece_jump']['raw_ratio']}×", "g_harm": f"{N['greece_jump']['harm_ratio']}×",
        "p_raw": f"{N['portugal_jump']['raw_ratio']}", "p_harm": f"{N['portugal_jump']['harm_ratio']}",
        "ncal": f"{N['n_cal_years']}", "chosen": N["chosen_model"],
        "g07": f"August 2007, Greece: {g07['value']:,} hotspots", "g07x": f"{g07['times_typical']}× a typical August",
        "unc": f"{N['uncertainty_month_pct']}%", "g07raw": f"{g07['raw']:,}", "g21raw": f"{N['stories']['greece_2021_08']['raw']:,}",
        "err": f"{N['err_raw_month_pct']}% → {N['err_harm_month_pct']}%", "col": f"{N['colour_agree_pct']}%",
        "yr": f"±{N['err_harm_year_pct']}%", "ta": f"{N['terra_aqua_mdape_pct']}% error",
    }
    bad = 0
    for k, exp in expected.items():
        got = used.get(k)
        ok = got == exp and exp in blob
        print(f"{'OK ' if ok else 'BAD'} {k:8s} expected '{exp}' slide '{got}'")
        bad += not ok
    print("All slide numbers match the data." if not bad else f"{bad} mismatches.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
