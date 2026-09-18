#!/usr/bin/env python3
"""Apply an issue-comment status command to the training CSV."""

from __future__ import annotations

import argparse
import csv
import os
import re
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Sequence


AGENDA_COLUMNS = (
    "day",
    "topic",
    "focus",
    "how_to_cover",
    "practice",
    "resource",
)
STATUS_ALIASES = {
    "notstarted": "not-started",
    "todo": "not-started",
    "pending": "not-started",
    "notdone": "not-started",
    "inprogress": "in-progress",
    "doing": "in-progress",
    "active": "in-progress",
    "done": "done",
    "complete": "done",
    "completed": "done",
    "finished": "done",
    "blocked": "blocked",
}
ASSIGNMENT_RE = re.compile(
    r"^\s*(?P<person>.+?)(?:\s*[-:_]\s*|\s+)"
    r"(?P<status>[A-Za-z][A-Za-z0-9_-]*)\s*$"
)


class CommandError(ValueError):
    """Raised when a status command cannot be applied safely."""


@dataclass(frozen=True)
class ParsedCommand:
    topic: str
    updates: Mapping[str, str]


@dataclass(frozen=True)
class UpdateResult:
    changed: bool
    message: str


def _normalize_identifier(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", value.casefold())


def _normalize_topic(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.casefold()).strip()


def _normalize_status(value: str) -> str:
    key = _normalize_identifier(value)
    try:
        return STATUS_ALIASES[key]
    except KeyError as exc:
        allowed = ", ".join(sorted({"not-started", "in-progress", "done", "blocked"}))
        raise CommandError(
            f"unknown status {value!r}; use one of: {allowed}"
        ) from exc


def _status_columns(fieldnames: Sequence[str]) -> list[str]:
    columns = [name for name in fieldnames if name not in AGENDA_COLUMNS]
    if not columns:
        raise CommandError(
            "the CSV must contain at least one learner column after the agenda columns"
        )
    return columns


def _person_aliases(header: str) -> set[str]:
    aliases = {_normalize_identifier(header)}
    match = re.fullmatch(r"person(\d+)", aliases.pop())
    normalized = _normalize_identifier(header)
    aliases.add(normalized)
    if match:
        aliases.add(f"p{match.group(1)}")
    return aliases


def _resolve_person(raw_name: str, columns: Sequence[str]) -> str:
    wanted = _normalize_identifier(raw_name)
    matches = [column for column in columns if wanted in _person_aliases(column)]
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise CommandError(f"person {raw_name!r} matches more than one learner column")
    expected = ", ".join(columns)
    raise CommandError(f"unknown person {raw_name!r}; use one of: {expected}")


def _looks_like_assignment(value: str) -> bool:
    return ASSIGNMENT_RE.fullmatch(value) is not None


def parse_status_comment(
    comment: str, fieldnames: Sequence[str]
) -> ParsedCommand | None:
    """Parse ``topic, person-status`` text, or return None for normal comments."""

    parts = [part.strip() for part in comment.split(",")]
    if len(parts) < 2 or not any(_looks_like_assignment(part) for part in parts[1:]):
        return None
    if not parts[0]:
        raise CommandError("the command must start with a topic or day number")

    columns = _status_columns(fieldnames)
    updates: dict[str, str] = {}
    for raw_update in parts[1:]:
        match = ASSIGNMENT_RE.fullmatch(raw_update)
        if match is None:
            raise CommandError(
                f"invalid update {raw_update!r}; use "
                "'person1-inprogress' or 'Person 1: done'"
            )
        person = _resolve_person(match.group("person"), columns)
        status = _normalize_status(match.group("status"))
        previous = updates.get(person)
        if previous is not None and previous != status:
            raise CommandError(f"person {person!r} is assigned conflicting statuses")
        updates[person] = status

    return ParsedCommand(topic=parts[0], updates=updates)


def _find_topic(rows: Sequence[Mapping[str, str]], requested: str) -> int:
    wanted = _normalize_topic(requested)
    matches: list[int] = []
    for index, row in enumerate(rows):
        topic = _normalize_topic(row.get("topic", ""))
        day = _normalize_topic(row.get("day", ""))
        candidates = {topic, day, f"day {day}"}
        if wanted in candidates:
            matches.append(index)
    if len(matches) == 1:
        return matches[0]
    if len(matches) > 1:
        raise CommandError(f"topic {requested!r} matches more than one agenda row")
    examples = ", ".join(
        f"Day {row.get('day', '?')} ({row.get('topic', 'untitled')})"
        for row in rows[:5]
    )
    raise CommandError(
        f"topic {requested!r} was not found; use an exact topic or Day N "
        f"(examples: {examples})"
    )


def _write_rows(path: Path, fieldnames: Sequence[str], rows: Sequence[Mapping[str, str]]) -> None:
    directory = path.parent
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="",
        dir=directory,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    ) as temporary:
        temporary_path = Path(temporary.name)
        writer = csv.DictWriter(
            temporary,
            fieldnames=fieldnames,
            lineterminator="\n",
            extrasaction="raise",
        )
        writer.writeheader()
        writer.writerows(rows)
    os.replace(temporary_path, path)


def apply_comment(csv_path: Path, comment: str) -> UpdateResult:
    """Apply one comment and atomically rewrite the CSV only when it changes."""

    try:
        with csv_path.open("r", encoding="utf-8-sig", newline="") as source:
            reader = csv.DictReader(source)
            if reader.fieldnames is None:
                raise CommandError("the CSV is missing its header row")
            missing = [column for column in AGENDA_COLUMNS if column not in reader.fieldnames]
            if missing:
                raise CommandError(
                    f"the CSV is missing required columns: {', '.join(missing)}"
                )
            rows = list(reader)
    except OSError as exc:
        raise CommandError(f"could not read {csv_path}: {exc}") from exc

    command = parse_status_comment(comment, reader.fieldnames)
    if command is None:
        return UpdateResult(False, "No status command detected; nothing to update.")
    row_index = _find_topic(rows, command.topic)
    row = rows[row_index]
    changes: list[str] = []
    for person, status in command.updates.items():
        if row[person] != status:
            changes.append(f"{person}: {row[person] or 'blank'} -> {status}")
            row[person] = status

    if not changes:
        return UpdateResult(
            False,
            f"No changes needed for Day {row['day']} ({row['topic']}).",
        )

    try:
        _write_rows(csv_path, reader.fieldnames, rows)
    except OSError as exc:
        raise CommandError(f"could not write {csv_path}: {exc}") from exc
    return UpdateResult(
        True,
        f"Updated Day {row['day']} ({row['topic']}): " + "; ".join(changes),
    )


def _default_csv_path() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "training.csv"


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Apply a training status issue comment to the agenda CSV."
    )
    parser.add_argument(
        "--comment",
        required=True,
        help="Comment text, for example: 'Day 1, person1-inprogress, person2-done'",
    )
    parser.add_argument(
        "--csv",
        type=Path,
        default=_default_csv_path(),
        help="CSV path (defaults to data/training.csv)",
    )
    args = parser.parse_args(argv)
    try:
        result = apply_comment(args.csv, args.comment)
    except CommandError as exc:
        print(f"Status command error: {exc}", file=sys.stderr)
        return 2
    print(result.message)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
