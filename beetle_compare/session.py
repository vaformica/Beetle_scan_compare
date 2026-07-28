"""Review decisions and auditable CSV outputs."""

from __future__ import annotations

import csv
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from .matching import Match, MatchResult


@dataclass
class Decision:
    match: Match
    status: str
    reviewed_at: str


class ReviewSession:
    def __init__(self, result: MatchResult, working_directory: Path):
        self.result = result
        self.decisions: dict[int, Decision] = {}
        self.working_directory = working_directory
        working_directory.mkdir(parents=True, exist_ok=True)

    def decide(self, index: int, status: str) -> None:
        if status not in {"approved", "rejected"}:
            raise ValueError(f"Unsupported decision: {status}")
        self.decisions[index] = Decision(
            self.result.matches[index],
            status,
            datetime.now(timezone.utc).isoformat(),
        )
        self.write_temporary_csv()

    def write_temporary_csv(self) -> Path:
        path = self.working_directory / "current_review.csv"
        with path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["left_file", "right_file", "match_score", "decision", "reviewed_at"])
            for index in sorted(self.decisions):
                decision = self.decisions[index]
                match = decision.match
                writer.writerow(
                    [match.left.path, match.right.path, f"{match.score:.2f}", decision.status, decision.reviewed_at]
                )
        return path

    def export(self, destination: Path) -> tuple[Path, Path]:
        destination.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
        decisions_path = destination / f"review_decisions_{stamp}.csv"
        unmatched_path = destination / f"unmatched_images_{stamp}.csv"
        with decisions_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["left_file", "right_file", "match_score", "decision", "reviewed_at"])
            for index, match in enumerate(self.result.matches):
                decision = self.decisions.get(index)
                writer.writerow(
                    [
                        match.left.path,
                        match.right.path,
                        f"{match.score:.2f}",
                        decision.status if decision else "not_reviewed",
                        decision.reviewed_at if decision else "",
                    ]
                )
        with unmatched_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["folder_side", "file", "reason"])
            for item in self.result.left_unmatched:
                writer.writerow(["left", item.path, "no unambiguous match"])
            for item in self.result.right_unmatched:
                writer.writerow(["right", item.path, "no unambiguous match"])
        return decisions_path, unmatched_path
