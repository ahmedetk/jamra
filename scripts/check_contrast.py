"""WCAG 2.x contrast check for the jamra Design v3 palette (light theme, one calm orange).

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
    ("body text on white", "#111827", "#FFFFFF", 4.5),
    ("body text on off-white band", "#111827", "#F7F7F5", 4.5),
    ("secondary text on white", "#4B5563", "#FFFFFF", 4.5),
    ("secondary text on off-white", "#4B5563", "#F7F7F5", 4.5),
    ("primary button text (dark on orange)", "#111827", "#E8833A", 4.5),
    ("primary button hover text", "#111827", "#C96A28", 4.5),
    ("secondary button text (white button)", "#111827", "#FFFFFF", 4.5),
    ("pressed chip / segment (white on ink)", "#FFFFFF", "#111827", 4.5),
    ("nav text", "#4B5563", "#FFFFFF", 4.5),
    ("hero headline on space", "#FFFFFF", "#03050A", 4.5),
    ("live chip text on space", "#E5E7EB", "#03050A", 4.5),
    ("image credit on space", "#9CA3AF", "#03050A", 4.5),
    ("level: normal", "#111827", "#F3F4F6", 4.5),
    ("level: elevated", "#7A3510", "#FCE7D6", 4.5),
    ("level: high", "#111827", "#E8833A", 4.5),
    ("level: extreme", "#FFFFFF", "#9A4A16", 4.5),
    ("value tag: observed", "#1F2F4A", "#EEF2F8", 4.5),
    ("control border on white", "#8B929C", "#FFFFFF", 3.0),
    ("focus ring on white", "#111827", "#FFFFFF", 3.0),
    ("focus ring on space", "#FFFFFF", "#03050A", 3.0),
    ("chart bars slate on white", "#5B7DB1", "#FFFFFF", 3.0),
    ("hotspot dot on Blue Marble ocean", "#E8833A", "#0B1F3A", 3.0),
]
CAL = {"much_lower": "#5B7DB1", "lower": "#B7C6DE", "typical": "#E5E7EB", "higher": "#F5BE93", "much_higher": "#E8833A"}


def main():
    bad = 0
    for what, fg, bg, need in PAIRS:
        r = ratio(fg, bg)
        ok = r >= need
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} {r:5.2f}:1 (need {need}) {what}: {fg} on {bg}")
    # calendar anomaly cells: symbols (graphics, 3:1) drawn in the better of dark or white (textOn in colors.js)
    for name, hx in CAL.items():
        r = max(ratio("#111827", hx), ratio("#FFFFFF", hx))
        print(f"{'OK ' if r >= 3 else 'BAD'} {r:5.2f}:1 best symbol colour on calendar '{name}' {hx}")
        bad += r < 3
    print("All pairs pass WCAG AA." if not bad else f"{bad} pair(s) fail.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
