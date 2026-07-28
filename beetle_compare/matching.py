"""Conservative filename matching for paired beetle scan images."""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass
from difflib import SequenceMatcher
from pathlib import Path

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp", ".webp"}
VIEW_LABELS = {"D": "dorsal", "V": "ventral", "R": "right"}
_VIEW_RE = re.compile(r"(?i)(?:^|[-_\s])(D|V|R)(?=$|[-_\s])")


@dataclass(frozen=True)
class ImageRecord:
    path: Path
    view: str
    match_key: str


@dataclass(frozen=True)
class Match:
    left: ImageRecord
    right: ImageRecord
    score: float


@dataclass(frozen=True)
class MatchResult:
    matches: list[Match]
    left_unmatched: list[ImageRecord]
    right_unmatched: list[ImageRecord]


def detect_view(path: Path) -> str | None:
    """Return D, V, or R when the stem contains a delimited view marker."""
    matches = list(_VIEW_RE.finditer(path.stem))
    return matches[-1].group(1).upper() if matches else None


def make_match_key(path: Path) -> str:
    """Normalize a stem while retaining beetle-identifying characters."""
    stem = _VIEW_RE.sub(" ", path.stem)
    return re.sub(r"[^a-z0-9]+", "", stem.casefold())


def scan_folder(folder: Path, view: str, recursive: bool = False) -> list[ImageRecord]:
    """Read image paths only; source files are never modified."""
    iterator: Iterable[Path] = folder.rglob("*") if recursive else folder.iterdir()
    records = []
    for path in iterator:
        if path.is_file() and path.suffix.casefold() in IMAGE_EXTENSIONS:
            detected = detect_view(path)
            if detected == view:
                records.append(ImageRecord(path, detected, make_match_key(path)))
    return sorted(records, key=lambda item: item.path.name.casefold())


def similarity(left: str, right: str) -> float:
    return SequenceMatcher(None, left, right, autojunk=False).ratio() * 100


def match_records(
    left: list[ImageRecord],
    right: list[ImageRecord],
    threshold: float = 82,
    ambiguity_margin: float = 3,
) -> MatchResult:
    """Create one-to-one matches, requiring a clear best choice on both sides."""
    candidates: list[tuple[float, int, int]] = []
    for li, left_item in enumerate(left):
        for ri, right_item in enumerate(right):
            score = similarity(left_item.match_key, right_item.match_key)
            if score >= threshold:
                candidates.append((score, li, ri))

    left_scores: dict[int, list[float]] = {}
    right_scores: dict[int, list[float]] = {}
    for score, li, ri in candidates:
        left_scores.setdefault(li, []).append(score)
        right_scores.setdefault(ri, []).append(score)
    for scores in (*left_scores.values(), *right_scores.values()):
        scores.sort(reverse=True)

    used_left: set[int] = set()
    used_right: set[int] = set()
    matches: list[Match] = []
    for score, li, ri in sorted(candidates, reverse=True):
        if li in used_left or ri in used_right:
            continue
        left_runner_up = left_scores[li][1] if len(left_scores[li]) > 1 else -1
        right_runner_up = right_scores[ri][1] if len(right_scores[ri]) > 1 else -1
        if score - left_runner_up < ambiguity_margin or score - right_runner_up < ambiguity_margin:
            continue
        used_left.add(li)
        used_right.add(ri)
        matches.append(Match(left[li], right[ri], score))

    matches.sort(key=lambda item: item.left.path.name.casefold())
    return MatchResult(
        matches,
        [item for index, item in enumerate(left) if index not in used_left],
        [item for index, item in enumerate(right) if index not in used_right],
    )
