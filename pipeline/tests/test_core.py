"""Unit tests for the Jamra pipeline. Written with an AI coding assistant (Claude Code by Anthropic)."""
import pytest

from jamra import anomaly, harmonize
from jamra.firms import cell_id, cell_center, dedupe_key, filter_reason, month_index, month_label, sensor_code

ACFG = {
    "categories": {"much_lower": 10, "lower": 25, "higher": 75, "much_higher": 90},
    "small_count_min_abs": 3, "small_count_min_rel": 0.2,
    "warning_levels": {"elevated": 75, "high": 90, "extreme": 97.5},
}
FILTERS = {"keep_types": [0], "modis_min_confidence": 30, "viirs_confidence": ["n", "h"], "keep_day_and_night": True}


def test_sensor_codes():
    assert sensor_code("Aqua", "MODIS") == "A"
    assert sensor_code("Terra", "MODIS") == "T"
    assert sensor_code("N", "VIIRS") == "N"
    assert sensor_code("N20", "VIIRS") == "J"
    assert sensor_code("1", "VIIRS") == "J"
    assert sensor_code("N21", "VIIRS") == "K"
    assert sensor_code("???", "VIIRS") is None


def test_month_index_roundtrip():
    for y, m in [(2003, 1), (2012, 2), (2026, 12)]:
        assert month_label(month_index(y, m)) == f"{y}-{m:02d}"


def test_cell_id_and_center():
    lat, lon = cell_center(cell_id(38.567, 23.2978))
    assert abs(lat - 38.55) < 1e-9 and abs(lon - 23.25) < 1e-9
    assert cell_id(-0.01, -0.01) != cell_id(0.01, 0.01)


def test_filters():
    assert filter_reason({"type": "0", "confidence": "64"}, "A", FILTERS) is None
    assert filter_reason({"type": "2", "confidence": "64"}, "A", FILTERS) == "type_2"
    assert filter_reason({"type": "0", "confidence": "20"}, "A", FILTERS) == "low_confidence"
    assert filter_reason({"type": "0", "confidence": "n"}, "N", FILTERS) is None
    assert filter_reason({"type": "0", "confidence": "l"}, "N", FILTERS) == "low_confidence"
    assert filter_reason({"confidence": "nominal"}, "J", FILTERS) is None  # NRT rows have no type column


def test_dedupe_key_is_stable():
    a = {"latitude": "38.12345", "longitude": "23.5", "acq_date": "2026-11-13", "acq_time": "130", "satellite": "N20"}
    b = {**a, "latitude": "38.123449", "acq_time": "0130"}
    assert dedupe_key(a) == dedupe_key(b)


def rows_const(k=3.0):
    rows = []
    for y in range(2012, 2020):
        for c, base in (("X", 100), ("Y", 10)):
            for m in range(1, 13):
                M = base * (1 + (m % 4))
                rows.append({"country": c, "month": m, "year": y, "M": M, "V": k * M})
    return rows


def test_ratio_models_recover_constant_factor():
    rows = rows_const(3.0)
    for model in ("M1", "M2", "M3"):
        p = harmonize.fit(model, rows, lam=10)
        assert harmonize.predict(p, "X", 5, 50) == pytest.approx(150)


def test_shrinkage_pulls_toward_parent():
    assert harmonize.area_factor(0, 0, 2.5, 50) == pytest.approx(2.5)
    assert harmonize.area_factor(4000, 1000, 2.5, 50) == pytest.approx((4000 + 125) / 1050)
    assert harmonize.area_factor(4000, 1000, 2.5, 0) == pytest.approx(4.0)


def test_m4_and_m5_reasonable():
    rows = rows_const(2.0)
    for model in ("M4", "M5"):
        p = harmonize.fit(model, rows)
        assert 300 < harmonize.predict(p, "X", 3, 200) < 500


def test_quantile_mapping_monotonic():
    p = harmonize.fit("M5", rows_const(2.0))
    preds = [harmonize.predict(p, "X", 1, M) for M in (100, 200, 300, 400)]
    assert preds == sorted(preds)


def test_loyo_and_choice():
    res = harmonize.loyo(rows_const(3.0), ["M0", "M1", "M2", "M3"], [0, 10, 100])
    assert res["metrics"]["M1"]["monthly"]["mae"] == pytest.approx(0, abs=1e-9)
    assert res["metrics"]["M0"]["monthly"]["mae"] > 0
    chosen, _ = harmonize.choose_model({m: res["metrics"][m] for m in ("M1", "M2", "M3")})
    assert chosen == "M1"


def test_metrics_edge_cases():
    m = harmonize.metrics([(0, 0), (5, 0)])
    assert m["mdape"] is None and m["bias"] is None
    assert harmonize.metrics([]) == {}


def test_percentile_and_baseline():
    others = list(range(1, 11))
    assert anomaly.percentile_rank(11, others) == 100
    assert anomaly.percentile_rank(0, others) == 0
    assert anomaly.percentile_rank(5, others) == 45
    b = anomaly.baseline(others)
    assert b["median"] == 5.5 and b["p25"] == pytest.approx(3.25)


def test_categories_and_small_count_guard():
    others = list(range(100, 120))
    assert anomaly.category(500, others, ACFG) == "much_higher"
    assert anomaly.category(10, others, ACFG) == "much_lower"
    assert anomaly.category(110, others, ACFG) == "typical"
    assert anomaly.category(2, [0, 0, 1, 0, 1, 0, 2, 0], ACFG) == "typical"
    assert anomaly.category(None, others, ACFG) is None
    assert anomaly.category(5, [], ACFG) is None


def test_warning_levels():
    hist = list(range(10, 50))
    assert anomaly.warning_level(200, hist, ACFG)["level"] == "extreme"
    assert anomaly.warning_level(30, hist, ACFG)["level"] == "normal"
    assert anomaly.warning_level(5, hist, ACFG)["level"] == "normal"
    assert anomaly.warning_level(5, [], ACFG)["level"] == "unknown"


def test_season_start_and_trend():
    assert anomaly.season_start([0, 0, 0, 0, 5, 10, 30, 40, 10, 5, 0, 0]) == 6
    assert anomaly.season_start([0] * 12) is None
    ys = list(range(2003, 2023))
    assert anomaly.theil_sen(ys, [10 - 0.1 * (y - 2003) for y in ys]) == pytest.approx(-0.1)
    assert anomaly.mann_kendall([float(i) for i in range(20)])["p"] < 0.001
    assert anomaly.mann_kendall([5, 5, 5, 5])["p"] == 1.0


def test_ratio_uncertainty():
    assert harmonize.ratio_uncertainty([(10, 5), (20, 10)]) is None
    se = harmonize.ratio_uncertainty([(300, 100), (310, 100), (290, 100), (305, 100)])
    assert 0 < se < 0.05


def test_confusion_counts():
    from jamra import validate
    pool = {("R", 8): {y: 10 + y % 7 for y in range(2010, 2020)}}
    preds = [{"region": "R", "month": 8, "year": 2015, "V": 100, "P": 90},   # hit
             {"region": "R", "month": 8, "year": 2016, "V": 100, "P": 10},   # miss
             {"region": "R", "month": 8, "year": 2017, "V": 12, "P": 100}]   # false alarm
    c = validate.confusion(preds, pool, ACFG)
    assert (c["hits"], c["misses"], c["false_alarms"]) == (1, 1, 1)
    assert c["hit_rate"] == 0.5


def test_region_prediction_methods():
    from jamra import validate
    f = harmonize.fit("M3", rows_const(3.0), 10)
    r = {"region": "a", "country": "X", "month": 5, "year": 2020, "M": 10, "V": 0}
    assert validate.predict_region("baseline", r, {}, f, 50, True) == pytest.approx(30)
    # an area with much higher own ratio and lots of data moves toward its own ratio
    loc = validate.predict_region("local", r, {"a": (6000.0, 1000.0)}, f, 50, True)
    assert 30 < loc < 60
