from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from typing import Optional

from reminder.domain.config import (
    AppConfig,
    nonnegative_int,
    parse_active_hours,
    positive_float,
    positive_int,
)
from reminder.infrastructure.windows_runtime import SingleInstanceLock, focus_existing_control_window
from reminder.presentation.desktop_ui import DesktopReminderApp


APP_ID = "DesktopReminder"
DEFAULT_INTERVAL_MINUTES = 25.0
DEFAULT_MESSAGE = "该休息一下了"
DEFAULT_QUICK_CLOSE_CONFIRM_TEXT = "真的不缓缓眼睛吗"
DEFAULT_ACTIVE_HOURS = "9-12/13-18"
SETTINGS_FILE_NAME = "desktop_reminder_settings.json"


def _is_frozen() -> bool:
    return bool(getattr(sys, "frozen", False))


def _project_root() -> str:
    return os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _runtime_base_dir() -> str:
    if _is_frozen():
        return os.path.dirname(os.path.abspath(sys.executable))
    return _project_root()


def _resolve_default_tray_icon() -> Optional[str]:
    candidates: list[str] = []
    runtime_dir = _runtime_base_dir()
    candidates.append(os.path.join(runtime_dir, "tray_icon.ico"))

    meipass_dir = getattr(sys, "_MEIPASS", None)
    if meipass_dir:
        candidates.append(os.path.join(str(meipass_dir), "tray_icon.ico"))

    if not _is_frozen():
        candidates.append(os.path.join(_project_root(), "tray_icon.ico"))

    for path in candidates:
        abs_path = os.path.abspath(path)
        if os.path.exists(abs_path):
            return abs_path
    return None


def _instance_key() -> str:
    if _is_frozen():
        # Stable across onefile runs: exe path does not change.
        return os.path.abspath(sys.executable).lower()
    return os.path.abspath(os.path.join(_project_root(), "desktop_reminder.py")).lower()


def _settings_file_path() -> str:
    return os.path.join(_runtime_base_dir(), SETTINGS_FILE_NAME)


def _load_saved_ui_defaults(settings_file: str) -> tuple[float, str, str, str]:
    interval_minutes = DEFAULT_INTERVAL_MINUTES
    message = DEFAULT_MESSAGE
    quick_close_confirm_text = DEFAULT_QUICK_CLOSE_CONFIRM_TEXT
    active_hours = DEFAULT_ACTIVE_HOURS

    try:
        with open(settings_file, "r", encoding="utf-8") as fp:
            raw_data = json.load(fp)
    except (OSError, json.JSONDecodeError):
        return interval_minutes, message, active_hours, quick_close_confirm_text

    if not isinstance(raw_data, dict):
        return interval_minutes, message, active_hours, quick_close_confirm_text

    raw_interval = raw_data.get("interval_minutes")
    if raw_interval is not None:
        try:
            interval_minutes = positive_float(str(raw_interval))
        except (ValueError, argparse.ArgumentTypeError):
            pass

    raw_message = raw_data.get("message")
    if isinstance(raw_message, str):
        normalized_message = raw_message.strip()
        if normalized_message:
            message = normalized_message

    raw_quick_close_text = raw_data.get("quick_close_confirm_text")
    if isinstance(raw_quick_close_text, str):
        normalized_quick_close_text = raw_quick_close_text.strip()
        if normalized_quick_close_text:
            quick_close_confirm_text = normalized_quick_close_text

    raw_active_hours = raw_data.get("active_hours")
    if raw_active_hours is None:
        # Backward-compatible key for previous internal naming.
        raw_active_hours = raw_data.get("active_hours_text")
    if isinstance(raw_active_hours, str):
        try:
            _, normalized_hours = parse_active_hours(raw_active_hours)
            active_hours = normalized_hours
        except ValueError:
            pass

    return interval_minutes, message, active_hours, quick_close_confirm_text


def parse_args(argv: list[str]) -> AppConfig:
    default_tray_icon = _resolve_default_tray_icon()
    settings_file = _settings_file_path()
    (
        saved_interval,
        saved_message,
        saved_active_hours,
        saved_quick_close_confirm_text,
    ) = _load_saved_ui_defaults(settings_file)

    parser = argparse.ArgumentParser(
        description="Show a desktop reminder popup at a fixed interval."
    )
    parser.add_argument(
        "--interval-minutes",
        type=positive_float,
        default=saved_interval,
        help="Reminder interval in minutes. Default: 25",
    )
    parser.add_argument(
        "--message",
        default=saved_message,
        help="Reminder message text.",
    )
    parser.add_argument(
        "--quick-close-confirm-text",
        default=saved_quick_close_confirm_text,
        help="Confirm text shown when reminder is closed too quickly.",
    )
    parser.add_argument(
        "--show-on-start",
        action="store_true",
        help="Show the reminder immediately at startup.",
    )
    parser.add_argument(
        "--window-width",
        type=positive_int,
        default=320,
        help="Reminder window width in pixels. Default: 320",
    )
    parser.add_argument(
        "--window-height",
        type=positive_int,
        default=140,
        help="Reminder window height in pixels. Default: 140",
    )
    parser.add_argument(
        "--title",
        default="提醒",
        help="Reminder window title.",
    )
    parser.add_argument(
        "--log-file",
        default=None,
        help="Optional log file path. If provided, logs are appended to this file.",
    )
    parser.add_argument(
        "--pid-file",
        default=None,
        help="Optional PID file path for external stop scripts.",
    )
    parser.add_argument(
        "--tray-icon",
        default=default_tray_icon,
        help="Optional .ico path for tray icon. Defaults to tray_icon.ico if present.",
    )
    parser.add_argument(
        "--active-hours",
        default=saved_active_hours,
        help="Active hours like '9-12/13-18/19-21'. Default: 9-12/13-18",
    )
    parser.add_argument(
        "--log-retention-days",
        type=nonnegative_int,
        default=14,
        help="Delete reminder logs older than this many days. 0 disables age pruning.",
    )
    parser.add_argument(
        "--log-max-files",
        type=nonnegative_int,
        default=100,
        help="Keep at most this many reminder log files. 0 disables count pruning.",
    )
    parser.add_argument(
        "--show-control-window",
        action="store_true",
        help="Keep the control window visible instead of hiding taskbar icon.",
    )

    args = parser.parse_args(argv)
    try:
        active_ranges, active_text = parse_active_hours(args.active_hours)
    except ValueError as exc:
        parser.error(str(exc))
        active_ranges, active_text = [], ""

    return AppConfig(
        interval_minutes=args.interval_minutes,
        message=args.message,
        quick_close_confirm_text=args.quick_close_confirm_text,
        show_on_start=args.show_on_start,
        window_width=args.window_width,
        window_height=args.window_height,
        title=args.title,
        log_file=args.log_file,
        pid_file=args.pid_file,
        tray_icon_path=args.tray_icon,
        hide_taskbar_icon=not args.show_control_window,
        log_retention_days=args.log_retention_days,
        log_max_files=args.log_max_files,
        active_hours_text=active_text,
        active_hour_ranges=active_ranges,
        settings_file=settings_file,
    )


def main(argv: list[str]) -> int:
    config = parse_args(argv)

    lock_name = "Local\\" + APP_ID + "_" + hashlib.sha1(_instance_key().encode("utf-8")).hexdigest()
    single_lock = SingleInstanceLock(lock_name)
    if not single_lock.acquire():
        focus_existing_control_window("Desktop Reminder")
        print("Desktop reminder is already running. Activated existing window.", flush=True)
        return 2

    try:
        app = DesktopReminderApp(config)
        app.run()
        return 0
    finally:
        single_lock.release()


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
