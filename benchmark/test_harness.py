from benchmark.harness import _parse_pick


CANDIDATES = [
    "example/alpha@current",
    "example/alphabet@current",
    "other/beta-tool@1.0",
]


def test_parse_pick_accepts_one_complete_service_id():
    assert _parse_pick("example/alpha@current", CANDIDATES) == "example/alpha@current"
    assert (
        _parse_pick("I choose `other/beta-tool@1.0`.", CANDIDATES)
        == "other/beta-tool@1.0"
    )


def test_parse_pick_rejects_stems_and_substrings():
    assert _parse_pick("alpha", CANDIDATES) is None
    assert _parse_pick("example/alpha@currentish", CANDIDATES) is None


def test_parse_pick_rejects_ambiguous_multiple_ids():
    response = "example/alpha@current or other/beta-tool@1.0"
    assert _parse_pick(response, CANDIDATES) is None
