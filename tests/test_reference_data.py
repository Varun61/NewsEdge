"""Tests for externalised reference-data loading (reads the real data/reference files)."""

from app.processors.reference_data import load_dict, load_list, load_set


def test_fno_universe_loads_and_is_uppercased():
    fno = load_set("fno_universe", default={"PLACEHOLDER"})
    assert "RELIANCE" in fno and "TATASTEEL" in fno
    assert len(fno) > 150            # ~186 names
    assert "PLACEHOLDER" not in fno  # real file used, not the default


def test_bellwethers_load():
    bw = load_set("institutional_bellwethers", default=set())
    assert "HDFCBANK" in bw and "INFY" in bw


def test_marquee_buyers_preserve_case():
    buyers = load_list("marquee_buyers", default=["x"])
    assert any("gqg" in b for b in buyers)
    assert "x" not in buyers


def test_high_pledge_dict_loads():
    d = load_dict("high_pledge_watchlist", default={})
    assert "RPOWER" in d and isinstance(d["RPOWER"], (int, float))


def test_fda_map_loads():
    d = load_dict("fda_firm_symbol_map", default={})
    assert d.get("aurobindo") == "AUROPHARMA"


def test_missing_file_falls_back_to_default():
    assert load_set("does_not_exist_xyz", default={"ABC"}) == {"ABC"}
    assert load_list("does_not_exist_xyz", default=["a", "b"]) == ["a", "b"]
    assert load_dict("does_not_exist_xyz", default={"k": 1}) == {"k": 1}
