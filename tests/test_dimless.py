import pytest
import dimless


def test_number_reynolds():
    r = dimless.number("reynolds")
    assert r["id"] == "reynolds"
    assert r["symbol"] == r"\text{Re}"


def test_number_missing():
    with pytest.raises(Exception):
        dimless.number("nonexistent")


def test_quantities_returns_dict():
    q = dimless.quantities()
    assert isinstance(q, dict)
    assert "quantities" in q


def test_search_finds_reynolds():
    results = dimless.search("reynolds")
    ids = [r["id"] for r in results]
    assert "reynolds" in ids


def test_search_no_match():
    results = dimless.search("zzznomatch")
    assert results == []
