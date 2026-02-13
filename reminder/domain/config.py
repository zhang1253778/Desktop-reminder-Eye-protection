from __future__ import annotations

import argparse
from dataclasses import dataclass
from typing import Optional


def positive_float(value: str) -> float:
    """argparse validator for positive float values."""
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def positive_int(value: str) -> int:
    """argparse validator for positive integer values."""
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be > 0")
    return parsed


def nonnegative_int(value: str) -> int:
    """argparse validator for non-negative integer values."""
    parsed = int(value)
    if parsed < 0:
        raise argparse.ArgumentTypeError("must be >= 0")
    return parsed


def parse_active_hours(value: str) -> tuple[list[tuple[int, int]], str]:
    """Parse active-hour expression like '9-12/13-18/19-21'."""
    raw = value.strip()
    if not raw:
        return [], ""

    parts = [p.strip() for p in raw.split("/") if p.strip()]
    if not parts:
        return [], ""

    ranges: list[tuple[int, int]] = []
    normalized: list[str] = []
    for part in parts:
        if "-" not in part:
            raise ValueError(f"Invalid segment '{part}', expected 'start-end'")
        start_str, end_str = part.split("-", 1)
        try:
            start = int(start_str.strip())
            end = int(end_str.strip())
        except ValueError as exc:
            raise ValueError(f"Invalid segment '{part}', hours must be integers") from exc

        if not (0 <= start <= 23 and 0 <= end <= 23):
            raise ValueError(f"Invalid segment '{part}', hours must be in 0-23")

        ranges.append((start, end))
        normalized.append(f"{start}-{end}")

    return ranges, "/".join(normalized)


@dataclass
class AppConfig:
    interval_minutes: float
    message: str
    quick_close_confirm_text: str
    show_on_start: bool
    window_width: int
    window_height: int
    title: str
    log_file: Optional[str]
    pid_file: Optional[str]
    tray_icon_path: Optional[str]
    hide_taskbar_icon: bool
    log_retention_days: int
    log_max_files: int
    active_hours_text: str
    active_hour_ranges: list[tuple[int, int]]
    settings_file: Optional[str]
