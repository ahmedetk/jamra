"""WCAG 2.x contrast check for the Jamra charcoal + soft-orange palette.

Text needs 4.5:1 (normal) or 3:1 (large / bold >= 18.66 px); UI parts and graphics need 3:1.
Usage: python scripts/check_contrast.py   (exit code 1 if any pair fails)
Written with the help of an SI coding assistant (Claude Code).
"""
import sys


def lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [v / 12.92 if v <= 0.03928 else ((v + 0.055) / 1.055) ** 2.4 for v in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def ratio(a, b):
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


# (what, foreground, background, minimum)
PAIRS = [
    ("body text on page", "#1F2328", "#F3F4F6", 4.5),
    ("muted text on page", "#5C626B", "#F3F4F6", 4.5),
    ("muted text on card", "#5C626B", "#FFFFFF", 4.5),
    ("link / accent text on card", "#A8501C", "#FFFFFF", 4.5),
    ("link / accent text on page", "#A8501C", "#F3F4F6", 4.5),
    ("main button text (dark on orange)", "#1F2328", "#F28C4B", 4.5),
    ("main button hover text", "#1F2328", "#D9733A", 4.5),
    ("nav text on charcoal", "#E5E7EB", "#2B2F36", 4.5),
    ("band / footer text on charcoal", "#D1D5DB", "#2B2F36", 4.5),
    ("footer small print on charcoal", "#A3A9B2", "#2B2F36", 4.5),
    ("eyebrow orange on dark hero", "#F28C4B", "#1F2328", 4.5),
    ("eyebrow orange on hero end", "#F28C4B", "#2B2F36", 4.5),
    ("hero lead on dark hero", "#D1D5DB", "#1F2328", 4.5),
    ("pressed chip / segment (white on charcoal)", "#FFFFFF", "#2B2F36", 4.5),
    ("level: normal", "#2B2F36", "#E5E7EB", 4.5),
    ("level: elevated", "#7A3510", "#FDE6D6", 4.5),
    ("level: high", "#1F2328", "#F28C4B", 4.5),
    ("level: extreme", "#FFFFFF", "#8A3A10", 4.5),
    ("step number (white on orange ink)", "#FFFFFF", "#A8501C", 4.5),
    ("text on light highlight", "#1F2328", "#FDE6D6", 4.5),
    ("control border on card", "#8A9099", "#FFFFFF", 3.0),
    ("focus ring on card", "#D9733A", "#FFFFFF", 3.0),
    ("focus ring on charcoal", "#D9733A", "#2B2F36", 3.0),
    ("chart line orange on card", "#D9733A", "#FFFFFF", 3.0),
    ("chart bars slate-blue on card", "#4A6785", "#FFFFFF", 3.0),
    ("map labels on charcoal land", "#E5E7EB", "#2B2F36", 4.5),
    ("map area outline on charcoal", "#F28C4B", "#2B2F36", 3.0),
    ("hotspot on charcoal", "#F28C4B", "#2B2F36", 3.0),
    ("newest hotspot on charcoal", "#FBC6A0", "#2B2F36", 3.0),
    ("map boundaries on charcoal", "#8A9099", "#2B2F36", 3.0),
]


def main():
    bad = 0
    for what, fg, bg, need in PAIRS:
        r = ratio(fg, bg)
        ok = r >= need
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} {r:5.2f}:1 (need {need}) {what}: {fg} on {bg}")
    # calendar anomaly cells: text colour chosen by textOn() in colors.js
    for name, hx in {"much_lower": "#3E5C76", "lower": "#A9BCCD", "typical": "#E5E7EB", "higher": "#F7B990", "much_higher": "#D9733A"}.items():
        r = max(ratio("#1F2328", hx), ratio("#FFFFFF", hx))
        print(f"{'OK ' if r >= 4.5 else 'BAD'} {r:5.2f}:1 best text on calendar '{name}' {hx}")
        bad += r < 4.5
    print("All pairs pass WCAG AA." if not bad else f"{bad} pair(s) fail.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
