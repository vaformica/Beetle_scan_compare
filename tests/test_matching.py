from pathlib import Path

from beetle_compare.matching import ImageRecord, detect_view, make_match_key, match_records


def record(name: str) -> ImageRecord:
    path = Path(name)
    return ImageRecord(path, detect_view(path) or "D", make_match_key(path))


def test_view_detection_uses_delimited_marker():
    assert detect_view(Path("beetle-101-D.jpg")) == "D"
    assert detect_view(Path("DRAGON-101.jpg")) is None


def test_view_marker_does_not_affect_match_key():
    assert make_match_key(Path("Box-12_Beetle-4-D.jpg")) == make_match_key(Path("Box 12 Beetle 4 V.png"))


def test_close_names_match_one_to_one():
    result = match_records(
        [record("Box12-Beetle04-D.jpg")],
        [record("Box12_Beetle4-D.tif")],
        threshold=75,
    )
    assert len(result.matches) == 1
    assert not result.left_unmatched
    assert not result.right_unmatched


def test_ambiguous_matches_are_not_guessed():
    result = match_records(
        [record("beetle-100-D.jpg")],
        [record("beetle-100-a-D.jpg"), record("beetle-100-b-D.jpg")],
        threshold=70,
        ambiguity_margin=3,
    )
    assert not result.matches
    assert len(result.left_unmatched) == 1
    assert len(result.right_unmatched) == 2
