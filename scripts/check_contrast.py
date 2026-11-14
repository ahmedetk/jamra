"""WCAG 2.x contrast check for the jamra Design v4 palette (warm greys, vivid ember orange).

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
PAIRS = [  # Design v4: warm greys + vivid ember orange
    ("main text on page", "#2B2B2B", "#EFEEE9", 4.5),
    ("main text on surface", "#2B2B2B", "#F7F6F2", 4.5),
    ("secondary text on page", "#6B6A66", "#EFEEE9", 4.5),
    ("secondary text on surface", "#6B6A66", "#F7F6F2", 4.5),
    ("primary button: white 18px on deep ember", "#FFFFFF", "#D03E0D", 4.5),
    ("primary button hover", "#FFFFFF", "#B5360B", 4.5),
    ("secondary button / hover (surface on charcoal)", "#F7F6F2", "#2B2B2B", 4.5),
    ("pressed segment (surface on charcoal)", "#F7F6F2", "#2B2B2B", 4.5),
    ("unpressed segment text on its track", "#55544F", "#E6E3DC", 4.5),
    ("selected area chip text on light orange tint", "#2B2B2B", "#FCE3D8", 4.5),
    ("chip subtitle on tint", "#5A5955", "#FCE3D8", 4.5),
    ("level: normal", "#2B2B2B", "#E6E3DC", 4.5),
    ("level: elevated", "#8A2A0B", "#FCE3D8", 4.5),
    ("level: high", "#2B2B2B", "#F9A98A", 4.5),
    ("level: extreme", "#FFFFFF", "#C23A10", 4.5),
    ("value tag: observed", "#23384F", "#E3EBF2", 4.5),
    ("control border on surface", "#8E8B84", "#F7F6F2", 3.0),
    ("focus ring on page", "#D9430F", "#EFEEE9", 3.0),
    ("focus ring on surface", "#D9430F", "#F7F6F2", 3.0),
    ("map labels on land", "#2B2B2B", "#F3F1EB", 4.5),
    ("hotspot on land", "#F4511E", "#F3F1EB", 3.0),
    ("hotspot on water", "#F4511E", "#B7CADB", 2.0),
    ("chart bars (lower blue) on surface", "#4E77A6", "#F7F6F2", 3.0),
]
CAL = {"much_lower": "#4E77A6", "lower": "#B7CADB", "typical": "#E2DFD7", "higher": "#F9A98A", "much_higher": "#F4511E"}


def main():
    bad = 0
    for what, fg, bg, need in PAIRS:
        r = ratio(fg, bg)
        ok = r >= need
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} {r:5.2f}:1 (need {need}) {what}: {fg} on {bg}")
    # calendar anomaly cells: symbols (graphics, 3:1) drawn in the better of dark or white (textOn in colors.js)
    for name, hx in CAL.items():
        r = max(ratio("#2B2B2B", hx), ratio("#FFFFFF", hx))
        print(f"{'OK ' if r >= 3 else 'BAD'} {r:5.2f}:1 best symbol colour on calendar '{name}' {hx}")
        bad += r < 3
    print("All pairs pass WCAG AA." if not bad else f"{bad} pair(s) fail.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
