import csv
from pathlib import Path

from beetle_compare.matching import ImageRecord, Match, MatchResult
from beetle_compare.session import ReviewSession


def test_decision_is_written_immediately(tmp_path: Path):
    left = ImageRecord(Path("/left/a-D.jpg"), "D", "a")
    right = ImageRecord(Path("/right/a-D.jpg"), "D", "a")
    session = ReviewSession(MatchResult([Match(left, right, 100)], [], []), tmp_path)
    session.decide(0, "rejected")
    with (tmp_path / "current_review.csv").open() as handle:
        rows = list(csv.DictReader(handle))
    assert rows[0]["decision"] == "rejected"
