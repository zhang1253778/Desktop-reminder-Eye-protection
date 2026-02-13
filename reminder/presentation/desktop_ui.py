from __future__ import annotations

import argparse
import json
import os
import queue
import random
import sys
from datetime import datetime, timedelta
from time import monotonic
from typing import Optional

import tkinter as tk
from tkinter import messagebox

from reminder.domain.config import AppConfig, parse_active_hours, positive_float
from reminder.infrastructure.windows_runtime import WinTrayIcon

class DesktopReminderApp:
    """Periodic desktop reminder application."""

    CLOSE_ACTION_MINIMIZE = "minimize"
    CLOSE_ACTION_EXIT = "exit"
    QUICK_CLOSE_CONFIRM_SECONDS = 20.0
    FONT_FAMILY = "Microsoft YaHei UI"
    FONT_BODY = (FONT_FAMILY, 9)
    FONT_BODY_BOLD = (FONT_FAMILY, 9, "bold")
    FONT_MEDIUM = (FONT_FAMILY, 10)
    FONT_LARGE = (FONT_FAMILY, 11)
    FONT_TITLE = (FONT_FAMILY, 12, "bold")

    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self.root = tk.Tk()
        self.reminder_window: Optional[tk.Toplevel] = None
        self.settings_window: Optional[tk.Toplevel] = None
        self.next_timer_id: Optional[str] = None
        self.next_reminder_time: Optional[datetime] = None
        self.reminder_shown_monotonic: Optional[float] = None
        self.ui_event_queue: "queue.Queue[str]" = queue.Queue()
        self.tray_icon: Optional[WinTrayIcon] = None
        self.close_action_preference: Optional[str] = None
        self.status_var = tk.StringVar(value="等待首次提醒...")
        self.config_summary_var = tk.StringVar(value="")
        self.window_icon_path = self._resolve_icon_path(self.config.tray_icon_path)
        self.window_icon_image = self._create_window_icon_image()
        self._apply_window_icon(self.root)
        self._refresh_config_summary()
        self._setup_control_window()

    def run(self) -> None:
        self._rotate_log_files()
        self._write_pid_file()
        self._log(
            "Reminder app started "
            f"(interval={self.config.interval_minutes} minutes, "
            f"show_on_start={self.config.show_on_start}, "
            f"hide_taskbar_icon={self.config.hide_taskbar_icon}, "
            f"active_hours={self._active_hours_summary()})"
        )
        try:
            self._start_tray_icon()
            self.root.after(200, self._process_ui_events)
            if self.config.show_on_start:
                if self._is_within_active_hours(datetime.now()):
                    self.show_or_focus_reminder()
                else:
                    self._log("Skip startup reminder because current time is outside active hours.")
            self.schedule_next_reminder()
            if self.config.hide_taskbar_icon:
                self._hide_from_taskbar()
            self.root.mainloop()
        finally:
            self._remove_pid_file()

    def _setup_control_window(self) -> None:
        self.root.title("Desktop Reminder")
        self.root.geometry("520x275")
        self.root.resizable(False, False)
        self.root.protocol("WM_DELETE_WINDOW", self.on_control_window_close)

        container = tk.Frame(self.root, padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        title_label = tk.Label(
            container,
            text="桌面提醒程序正在运行",
            font=self.FONT_TITLE,
            anchor="w",
            justify=tk.LEFT,
        )
        title_label.pack(fill=tk.X)

        status_label = tk.Label(
            container,
            textvariable=self.status_var,
            anchor="w",
            justify=tk.LEFT,
            font=self.FONT_MEDIUM,
            wraplength=470,
        )
        status_label.pack(fill=tk.X, pady=(8, 10))

        config_card = tk.LabelFrame(
            container,
            text="当前设置",
            padx=10,
            pady=8,
            font=self.FONT_BODY_BOLD,
            labelanchor="n",
            bd=1,
        )
        config_card.pack(fill=tk.X, pady=(0, 12))

        config_label = tk.Label(
            config_card,
            textvariable=self.config_summary_var,
            anchor="w",
            justify=tk.LEFT,
            font=self.FONT_BODY,
            wraplength=450,
        )
        config_label.pack(fill=tk.X)

        button_row = tk.Frame(container)
        button_row.pack(fill=tk.X)
        button_row.grid_columnconfigure(0, weight=1)
        button_row.grid_columnconfigure(1, weight=1)
        button_row.grid_columnconfigure(2, weight=1)

        show_button = tk.Button(
            button_row,
            text="立即提醒",
            width=12,
            command=self.show_or_focus_reminder,
        )
        show_button.grid(row=0, column=0, sticky="ew")

        settings_button = tk.Button(
            button_row,
            text="设置",
            width=12,
            command=self.open_settings_window,
        )
        settings_button.grid(row=0, column=1, padx=8, sticky="ew")

        hide_button = tk.Button(
            button_row,
            text="隐藏窗口",
            width=12,
            command=self._hide_from_taskbar,
        )
        hide_button.grid(row=0, column=2, sticky="ew")

        hint_label = tk.Label(
            container,
            text=(
                '点击“设置”可配置提醒间隔、提醒文案和生效时段（含预设）。\n'
                '托盘图标在任务栏右下角 "^" 隐藏图标区域。'
            ),
            anchor="w",
            justify=tk.LEFT,
            font=self.FONT_BODY,
            wraplength=470,
        )
        hint_label.pack(fill=tk.X, pady=(10, 0))

    @staticmethod
    def _center_window_on_screen(window: tk.Toplevel, width: int, height: int) -> None:
        screen_w = window.winfo_screenwidth()
        screen_h = window.winfo_screenheight()
        pos_x = max(0, (screen_w - width) // 2)
        pos_y = max(0, (screen_h - height) // 2)
        window.geometry(f"{width}x{height}+{pos_x}+{pos_y}")

    def _resolve_icon_path(self, icon_path: Optional[str]) -> Optional[str]:
        if not icon_path:
            return None
        try:
            abs_path = os.path.abspath(icon_path)
            return abs_path if os.path.exists(abs_path) else None
        except OSError:
            return None

    def _create_window_icon_image(self) -> Optional[tk.PhotoImage]:
        # Do not force a generated fallback icon. When no .ico is provided,
        # let the OS/executable icon be used to keep icon consistency.
        return None

    def _apply_window_icon(self, window: tk.Tk | tk.Toplevel) -> None:
        if self.window_icon_path:
            try:
                window.iconbitmap(default=self.window_icon_path)
                return
            except tk.TclError:
                pass

        if self.window_icon_image is None:
            return
        try:
            window.iconphoto(True, self.window_icon_image)
        except tk.TclError:
            pass

    def _log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        line = f"[{timestamp}] {message}"
        try:
            print(line, flush=True)
        except Exception:
            # pythonw may not always expose stdout; file logging still works.
            pass
        if self.config.log_file:
            try:
                with open(self.config.log_file, "a", encoding="utf-8") as fp:
                    fp.write(line + "\n")
            except OSError:
                pass

    def _write_pid_file(self) -> None:
        if not self.config.pid_file:
            return
        try:
            with open(self.config.pid_file, "w", encoding="utf-8") as fp:
                fp.write(str(os.getpid()))
            self._log(f"PID file written: {self.config.pid_file}")
        except OSError:
            self._log(f"Failed to write PID file: {self.config.pid_file}")

    def _remove_pid_file(self) -> None:
        if not self.config.pid_file:
            return
        try:
            if os.path.exists(self.config.pid_file):
                os.remove(self.config.pid_file)
        except OSError:
            pass

    def _persist_runtime_settings(self) -> None:
        settings_file = self.config.settings_file
        if not settings_file:
            return

        serialized: dict[str, object] = {}
        try:
            if os.path.exists(settings_file):
                with open(settings_file, "r", encoding="utf-8") as fp:
                    raw = json.load(fp)
                if isinstance(raw, dict):
                    serialized = raw
        except (OSError, json.JSONDecodeError):
            serialized = {}

        serialized["interval_minutes"] = self.config.interval_minutes
        serialized["message"] = self.config.message
        serialized["quick_close_confirm_text"] = self.config.quick_close_confirm_text
        serialized["active_hours"] = self.config.active_hours_text

        try:
            settings_dir = os.path.dirname(os.path.abspath(settings_file))
            if settings_dir:
                os.makedirs(settings_dir, exist_ok=True)
            with open(settings_file, "w", encoding="utf-8") as fp:
                json.dump(serialized, fp, ensure_ascii=False, indent=2)
            self._log(f"Settings persisted to: {settings_file}")
        except OSError:
            self._log(f"Failed to persist settings to: {settings_file}")

    def _rotate_log_files(self) -> None:
        if not self.config.log_file:
            return

        current_log = os.path.abspath(self.config.log_file)
        log_dir = os.path.dirname(current_log)
        if not os.path.isdir(log_dir):
            return

        now_ts = datetime.now().timestamp()
        retention_seconds = self.config.log_retention_days * 86400

        candidates: list[tuple[str, float]] = []
        try:
            with os.scandir(log_dir) as it:
                for entry in it:
                    if not entry.is_file():
                        continue
                    if not entry.name.startswith("desktop_reminder_") or not entry.name.endswith(".log"):
                        continue
                    try:
                        candidates.append((entry.path, entry.stat().st_mtime))
                    except OSError:
                        continue
        except OSError:
            return

        delete_paths: set[str] = set()

        if self.config.log_retention_days > 0:
            cutoff_ts = now_ts - retention_seconds
            for path, mtime in candidates:
                if path == current_log:
                    continue
                if mtime < cutoff_ts:
                    delete_paths.add(path)

        remaining = [(p, m) for p, m in candidates if p not in delete_paths]
        if self.config.log_max_files > 0 and len(remaining) > self.config.log_max_files:
            remaining.sort(key=lambda x: x[1], reverse=True)
            for path, _ in remaining[self.config.log_max_files :]:
                if path != current_log:
                    delete_paths.add(path)

        for path in delete_paths:
            try:
                os.remove(path)
            except OSError:
                pass

    def _apply_close_action(self, action: str) -> None:
        if action == self.CLOSE_ACTION_EXIT:
            self.quit_app()
            return
        self._hide_from_taskbar()

    def _is_within_active_hours(self, current: datetime) -> bool:
        if not self.config.active_hour_ranges:
            return True
        hour = current.hour
        for start, end in self.config.active_hour_ranges:
            if start <= end:
                if start <= hour <= end:
                    return True
            else:
                # Cross-day range, e.g. 22-2
                if hour >= start or hour <= end:
                    return True
        return False

    def _active_hours_summary(self) -> str:
        return self.config.active_hours_text if self.config.active_hours_text else "全天"

    @staticmethod
    def _format_float(value: float) -> str:
        return str(int(value)) if float(value).is_integer() else f"{value:g}"

    def _refresh_config_summary(self) -> None:
        message_preview = self.config.message.strip().replace("\n", " ")
        if not message_preview:
            message_preview = "(空)"
        if len(message_preview) > 32:
            message_preview = message_preview[:32] + "..."
        self.config_summary_var.set(
            f"周期：每 {self._format_float(self.config.interval_minutes)} 分钟提醒\n"
            f"时段：{self._active_hours_summary()}\n"
            f"文案：{message_preview}"
        )

    def _update_tray_tooltip(self) -> None:
        if self.tray_icon is None:
            return
        if self.next_reminder_time is None:
            tooltip = "Desktop Reminder | 等待下一次提醒"
        else:
            tooltip = "Desktop Reminder | 下次提醒 " + self.next_reminder_time.strftime("%Y-%m-%d %H:%M:%S")
        self.tray_icon.update_tooltip(tooltip)

    def open_settings_window(self) -> None:
        if self.settings_window is not None and self.settings_window.winfo_exists():
            try:
                self.settings_window.deiconify()
                self.settings_window.lift()
                self.settings_window.focus_force()
            except tk.TclError:
                pass
            return

        dialog = tk.Toplevel(self.root)
        self._apply_window_icon(dialog)
        dialog.title("设置")
        dialog.resizable(False, False)
        try:
            if self.root.winfo_viewable():
                dialog.transient(self.root)
        except tk.TclError:
            pass
        dialog.grab_set()
        dialog_width = 500
        dialog_height = 300
        dialog.geometry(f"{dialog_width}x{dialog_height}")
        self._center_window_on_screen(dialog, dialog_width, dialog_height)
        dialog.lift()
        try:
            dialog.focus_force()
        except tk.TclError:
            pass
        self.settings_window = dialog

        interval_var = tk.StringVar(value=self._format_float(self.config.interval_minutes))
        message_var = tk.StringVar(value=self.config.message)
        quick_close_confirm_text_var = tk.StringVar(value=self.config.quick_close_confirm_text)
        active_hours_var = tk.StringVar(value=self.config.active_hours_text)

        container = tk.Frame(dialog, padx=14, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        interval_row = tk.Frame(container)
        interval_row.pack(fill=tk.X)
        interval_label = tk.Label(
            interval_row,
            text="提醒间隔(分钟)",
            width=12,
            anchor="w",
            justify=tk.LEFT,
            font=self.FONT_BODY,
        )
        interval_label.pack(side=tk.LEFT)
        interval_entry = tk.Entry(interval_row, textvariable=interval_var, font=self.FONT_BODY)
        interval_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        message_row = tk.Frame(container)
        message_row.pack(fill=tk.X, pady=(10, 0))
        message_label = tk.Label(
            message_row,
            text="提醒文案一",
            width=12,
            anchor="w",
            justify=tk.LEFT,
            font=self.FONT_BODY,
        )
        message_label.pack(side=tk.LEFT)
        message_entry = tk.Entry(message_row, textvariable=message_var, font=self.FONT_BODY)
        message_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        quick_close_row = tk.Frame(container)
        quick_close_row.pack(fill=tk.X, pady=(10, 0))
        quick_close_label = tk.Label(
            quick_close_row,
            text="提醒文案二",
            width=12,
            anchor="w",
            justify=tk.LEFT,
            font=self.FONT_BODY,
        )
        quick_close_label.pack(side=tk.LEFT)
        quick_close_entry = tk.Entry(
            quick_close_row,
            textvariable=quick_close_confirm_text_var,
            font=self.FONT_BODY,
        )
        quick_close_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        active_row = tk.Frame(container)
        active_row.pack(fill=tk.X, pady=(10, 0))
        active_label = tk.Label(
            active_row,
            text="生效时段",
            width=12,
            anchor="w",
            justify=tk.LEFT,
            font=self.FONT_BODY,
        )
        active_label.pack(side=tk.LEFT)
        active_entry = tk.Entry(active_row, textvariable=active_hours_var, font=self.FONT_BODY)
        active_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)

        active_hint = tk.Label(
            container,
            text='格式: 9-12/13-18/19-21，留空=全天生效',
            anchor="w",
            justify=tk.LEFT,
            font=self.FONT_BODY,
        )
        active_hint.pack(fill=tk.X, pady=(6, 0))

        preset_row = tk.Frame(container)
        preset_row.pack(fill=tk.X, pady=(8, 0))

        def use_preset(value: str, label: str) -> None:
            active_hours_var.set(value)
            self.status_var.set(f"已选择预设：{label}，点击“保存并应用”后生效。")

        preset_workday_btn = tk.Button(
            preset_row,
            text="工作日时段",
            width=11,
            command=lambda: use_preset("9-12/13-18", "工作日时段"),
        )
        preset_workday_btn.pack(side=tk.LEFT)

        preset_all_day_btn = tk.Button(
            preset_row,
            text="全天",
            width=8,
            command=lambda: use_preset("", "全天"),
        )
        preset_all_day_btn.pack(side=tk.LEFT, padx=(8, 0))

        def focus_custom() -> None:
            active_entry.focus_set()
            active_entry.selection_range(0, tk.END)
            active_entry.icursor(tk.END)
            self.status_var.set("请输入自定义时段后点击“保存并应用”，例如 9-12/13-18/19-21")

        preset_custom_btn = tk.Button(
            preset_row,
            text="自定义",
            width=8,
            command=focus_custom,
        )
        preset_custom_btn.pack(side=tk.LEFT, padx=(8, 0))

        button_row = tk.Frame(container)
        button_row.pack(fill=tk.X, pady=(14, 0))

        def close_dialog() -> None:
            if self.settings_window is dialog:
                self.settings_window = None
            try:
                dialog.grab_release()
            except tk.TclError:
                pass
            if dialog.winfo_exists():
                dialog.destroy()

        def save_and_apply() -> None:
            interval_text = interval_var.get().strip()
            try:
                interval_minutes = positive_float(interval_text)
            except (ValueError, argparse.ArgumentTypeError):
                messagebox.showerror("设置错误", "提醒间隔必须大于 0。", parent=dialog)
                interval_entry.focus_set()
                interval_entry.selection_range(0, tk.END)
                return

            message_text = message_var.get().strip()
            if not message_text:
                messagebox.showerror("设置错误", "提醒文案不能为空。", parent=dialog)
                message_entry.focus_set()
                message_entry.selection_range(0, tk.END)
                return

            quick_close_confirm_text = quick_close_confirm_text_var.get().strip()
            if not quick_close_confirm_text:
                messagebox.showerror("设置错误", "提醒文案二不能为空。", parent=dialog)
                quick_close_entry.focus_set()
                quick_close_entry.selection_range(0, tk.END)
                return

            active_text = active_hours_var.get().strip()
            try:
                active_ranges, active_text_normalized = parse_active_hours(active_text)
            except ValueError as exc:
                messagebox.showerror("时段格式错误", str(exc), parent=dialog)
                active_entry.focus_set()
                active_entry.selection_range(0, tk.END)
                return

            self.config.interval_minutes = interval_minutes
            self.config.message = message_text
            self.config.quick_close_confirm_text = quick_close_confirm_text
            self.config.active_hour_ranges = active_ranges
            self.config.active_hours_text = active_text_normalized
            self._refresh_config_summary()
            self._log(
                "Settings updated "
                f"(interval={self._format_float(self.config.interval_minutes)} minutes, "
                f"active_hours={self._active_hours_summary()})"
            )
            self._persist_runtime_settings()
            self.status_var.set("设置已保存并应用，下次启动仍然生效。")
            self.schedule_next_reminder()
            close_dialog()

        save_button = tk.Button(
            button_row,
            text="保存并应用",
            width=12,
            command=save_and_apply,
        )
        save_button.pack(side=tk.RIGHT)

        cancel_button = tk.Button(
            button_row,
            text="取消",
            width=10,
            command=close_dialog,
        )
        cancel_button.pack(side=tk.RIGHT, padx=(0, 8))

        dialog.protocol("WM_DELETE_WINDOW", close_dialog)

    def on_control_window_close(self) -> None:
        if self.close_action_preference in (self.CLOSE_ACTION_MINIMIZE, self.CLOSE_ACTION_EXIT):
            self._apply_close_action(self.close_action_preference)
            return
        self._show_close_choice_dialog()

    def _show_close_choice_dialog(self) -> None:
        dialog = tk.Toplevel(self.root)
        dialog.title("关闭程序")
        dialog.resizable(False, False)
        try:
            if self.root.winfo_viewable():
                dialog.transient(self.root)
        except tk.TclError:
            pass
        dialog.grab_set()
        dialog_width = 360
        dialog_height = 170
        dialog.geometry(f"{dialog_width}x{dialog_height}")
        self._center_window_on_screen(dialog, dialog_width, dialog_height)
        dialog.lift()
        try:
            dialog.focus_force()
        except tk.TclError:
            pass

        remember_var = tk.BooleanVar(value=False)

        container = tk.Frame(dialog, padx=14, pady=12)
        container.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(
            container,
            text="关闭控制窗口时，你希望执行哪个操作？",
            anchor="w",
            justify=tk.LEFT,
            font=self.FONT_MEDIUM,
        )
        label.pack(fill=tk.X, pady=(0, 10))

        remember_check = tk.Checkbutton(
            container,
            text="本次运行记住我的选择",
            variable=remember_var,
            anchor="w",
            justify=tk.LEFT,
            font=self.FONT_BODY,
        )
        remember_check.pack(fill=tk.X, pady=(0, 10))

        button_row = tk.Frame(container)
        button_row.pack(fill=tk.X, pady=(4, 0))

        def choose_and_close(action: str) -> None:
            if remember_var.get():
                self.close_action_preference = action
            else:
                self.close_action_preference = None
            dialog.destroy()
            self._apply_close_action(action)

        minimize_btn = tk.Button(
            button_row,
            text="隐藏到托盘",
            width=12,
            command=lambda: choose_and_close(self.CLOSE_ACTION_MINIMIZE),
        )
        minimize_btn.pack(side=tk.LEFT)

        exit_btn = tk.Button(
            button_row,
            text="退出程序",
            width=12,
            command=lambda: choose_and_close(self.CLOSE_ACTION_EXIT),
        )
        exit_btn.pack(side=tk.RIGHT)

        cancel_btn = tk.Button(
            container,
            text="取消",
            width=10,
            command=dialog.destroy,
        )
        cancel_btn.pack(side=tk.RIGHT, pady=(12, 0))

    def _hide_from_taskbar(self) -> None:
        try:
            self.root.withdraw()
            self._log("Control window hidden from taskbar.")
        except tk.TclError:
            pass

    def _show_control_window(self) -> None:
        try:
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()
            self._log("Control window shown from tray icon.")
        except tk.TclError:
            pass

    def _show_settings_from_tray(self) -> None:
        try:
            self.open_settings_window()
            self._log("Settings window shown from tray menu.")
        except tk.TclError:
            pass

    def _start_tray_icon(self) -> None:
        if sys.platform != "win32":
            self._log("Tray icon is only available on Windows.")
            return

        self.tray_icon = WinTrayIcon(
            tooltip="Desktop Reminder",
            icon_path=self.config.tray_icon_path,
            on_show=lambda: self.ui_event_queue.put("show_control"),
            on_settings=lambda: self.ui_event_queue.put("show_settings"),
            on_exit=lambda: self.ui_event_queue.put("exit_app"),
            logger=self._log,
        )
        if not self.tray_icon.start():
            self._log("Tray icon failed to start.")
            self.tray_icon = None

    def _process_ui_events(self) -> None:
        try:
            while True:
                event = self.ui_event_queue.get_nowait()
                if event == "show_control":
                    self._show_control_window()
                elif event == "show_settings":
                    self._show_settings_from_tray()
                elif event == "exit_app":
                    self.quit_app()
        except queue.Empty:
            pass
        try:
            self.root.after(200, self._process_ui_events)
        except tk.TclError:
            pass

    def schedule_next_reminder(self) -> None:
        interval_ms = int(self.config.interval_minutes * 60 * 1000)
        if self.next_timer_id is not None:
            self.root.after_cancel(self.next_timer_id)
        self.next_timer_id = self.root.after(interval_ms, self._on_timer)
        self.next_reminder_time = datetime.now() + timedelta(milliseconds=interval_ms)
        self.status_var.set(f"下次提醒：{self.next_reminder_time.strftime('%Y-%m-%d %H:%M:%S')}")
        self._update_tray_tooltip()
        self._log(
            f"Next reminder scheduled at {self.next_reminder_time.strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def _on_timer(self) -> None:
        self.next_timer_id = None
        now = datetime.now()
        if self._is_within_active_hours(now):
            self.show_or_focus_reminder()
        else:
            self.status_var.set(f"当前不在生效时段（{self._active_hours_summary()}），本次跳过。")
            self._log("Reminder skipped because current time is outside active hours.")
        self.schedule_next_reminder()

    def show_or_focus_reminder(self) -> None:
        if self.reminder_window is not None and self.reminder_window.winfo_exists():
            self._log("Reminder already open. Bringing existing window to front.")
            self.status_var.set("提醒窗口已存在，已置顶显示。")
            self._focus_existing_window()
            return

        self.reminder_window = tk.Toplevel(self.root)
        self._apply_window_icon(self.reminder_window)
        self.reminder_window.title(self.config.title)
        self.reminder_window.resizable(False, False)
        self.reminder_window.attributes("-topmost", True)
        self.reminder_window.protocol("WM_DELETE_WINDOW", self.on_reminder_close)

        screen_w = self.root.winfo_screenwidth()
        screen_h = self.root.winfo_screenheight()
        pos_x, pos_y = self.compute_random_position(
            screen_w, screen_h, self.config.window_width, self.config.window_height
        )
        self.reminder_window.geometry(
            f"{self.config.window_width}x{self.config.window_height}+{pos_x}+{pos_y}"
        )

        container = tk.Frame(self.reminder_window, padx=16, pady=14)
        container.pack(fill=tk.BOTH, expand=True)

        label = tk.Label(
            container,
            text=self.config.message,
            justify=tk.LEFT,
            anchor="w",
            wraplength=max(120, self.config.window_width - 32),
            font=self.FONT_LARGE,
        )
        label.pack(fill=tk.BOTH, expand=True)

        self.reminder_window.update_idletasks()
        self._focus_existing_window()
        self.reminder_shown_monotonic = monotonic()
        self.status_var.set("提醒窗口已弹出，等待手动点击 × 关闭。")
        self._log(f"Reminder shown at x={pos_x}, y={pos_y}")

    def _focus_existing_window(self) -> None:
        if self.reminder_window is None or not self.reminder_window.winfo_exists():
            return
        self.reminder_window.deiconify()
        self.reminder_window.attributes("-topmost", True)
        self.reminder_window.lift()
        try:
            self.reminder_window.focus_force()
        except tk.TclError:
            # focus_force can fail on some desktop states; window is still shown.
            pass

    @staticmethod
    def compute_random_position(
        screen_w: int, screen_h: int, win_w: int, win_h: int
    ) -> tuple[int, int]:
        max_x = max(0, screen_w - win_w)
        max_y = max(0, screen_h - win_h)
        return random.randint(0, max_x), random.randint(0, max_y)

    def on_reminder_close(self) -> None:
        if self.reminder_window is None:
            return

        if (
            self.reminder_shown_monotonic is not None
            and monotonic() - self.reminder_shown_monotonic < self.QUICK_CLOSE_CONFIRM_SECONDS
        ):
            try:
                should_close = messagebox.askyesno(
                    "确认关闭",
                    self.config.quick_close_confirm_text,
                    parent=self.reminder_window,
                )
            except tk.TclError:
                should_close = True
            if not should_close:
                self.status_var.set("已保留提醒窗口，记得活动一下眼睛。")
                self._log("Quick-close canceled by user; reminder window kept open.")
                self._focus_existing_window()
                return

        if self.reminder_window.winfo_exists():
            self.reminder_window.destroy()
        self.reminder_window = None
        self.reminder_shown_monotonic = None
        if self.next_reminder_time is not None:
            self.status_var.set(
                f"下次提醒：{self.next_reminder_time.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        else:
            self.status_var.set("等待下一次提醒...")
        self._log("Reminder window closed by user.")

    def quit_app(self) -> None:
        self._log("Exit requested by user. Shutting down.")
        if self.tray_icon is not None:
            self.tray_icon.stop()
            self.tray_icon = None
        if self.next_timer_id is not None:
            try:
                self.root.after_cancel(self.next_timer_id)
            except tk.TclError:
                pass
            self.next_timer_id = None
        if self.reminder_window is not None and self.reminder_window.winfo_exists():
            try:
                self.reminder_window.destroy()
            except tk.TclError:
                pass
        self.reminder_window = None
        self.reminder_shown_monotonic = None
        try:
            self.root.destroy()
        except tk.TclError:
            pass
