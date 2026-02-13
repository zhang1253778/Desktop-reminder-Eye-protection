from __future__ import annotations

import os
import sys
import threading
from typing import Callable, Optional

if sys.platform == "win32":
    import ctypes
    from ctypes import wintypes

    LRESULT = ctypes.c_longlong if ctypes.sizeof(ctypes.c_void_p) == 8 else ctypes.c_long
    HINSTANCE = getattr(wintypes, "HINSTANCE", wintypes.HANDLE)
    HANDLE = getattr(wintypes, "HANDLE", ctypes.c_void_p)
    HICON = getattr(wintypes, "HICON", wintypes.HANDLE)
    HCURSOR = getattr(wintypes, "HCURSOR", wintypes.HANDLE)
    HBRUSH = getattr(wintypes, "HBRUSH", wintypes.HANDLE)
    HMENU = getattr(wintypes, "HMENU", wintypes.HANDLE)
    UINT_PTR = ctypes.c_size_t
    ATOM = getattr(wintypes, "ATOM", wintypes.WORD)
    LPCRECT = getattr(wintypes, "LPCRECT", getattr(wintypes, "LPRECT", wintypes.LPVOID))
    IMAGE_ICON = 1
    LR_LOADFROMFILE = 0x00000010
    LR_DEFAULTSIZE = 0x00000040
    ERROR_ALREADY_EXISTS = 183
    SW_RESTORE = 9
    SW_SHOW = 5

    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class MSG(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("message", wintypes.UINT),
            ("wParam", wintypes.WPARAM),
            ("lParam", wintypes.LPARAM),
            ("time", wintypes.DWORD),
            ("pt", POINT),
            ("lPrivate", wintypes.DWORD),
        ]

    WNDPROC = ctypes.WINFUNCTYPE(
        LRESULT,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )

    class WNDCLASSW(ctypes.Structure):
        _fields_ = [
            ("style", wintypes.UINT),
            ("lpfnWndProc", WNDPROC),
            ("cbClsExtra", ctypes.c_int),
            ("cbWndExtra", ctypes.c_int),
            ("hInstance", HINSTANCE),
            ("hIcon", HICON),
            ("hCursor", HCURSOR),
            ("hbrBackground", HBRUSH),
            ("lpszMenuName", wintypes.LPCWSTR),
            ("lpszClassName", wintypes.LPCWSTR),
        ]

    class GUID(ctypes.Structure):
        _fields_ = [
            ("Data1", wintypes.DWORD),
            ("Data2", wintypes.WORD),
            ("Data3", wintypes.WORD),
            ("Data4", ctypes.c_ubyte * 8),
        ]

    class NOTIFYICONDATAW(ctypes.Structure):
        _fields_ = [
            ("cbSize", wintypes.DWORD),
            ("hWnd", wintypes.HWND),
            ("uID", wintypes.UINT),
            ("uFlags", wintypes.UINT),
            ("uCallbackMessage", wintypes.UINT),
            ("hIcon", HICON),
            ("szTip", wintypes.WCHAR * 128),
            ("dwState", wintypes.DWORD),
            ("dwStateMask", wintypes.DWORD),
            ("szInfo", wintypes.WCHAR * 256),
            ("uTimeoutOrVersion", wintypes.UINT),
            ("szInfoTitle", wintypes.WCHAR * 64),
            ("dwInfoFlags", wintypes.DWORD),
            ("guidItem", GUID),
            ("hBalloonIcon", HICON),
        ]

    _user32 = ctypes.windll.user32
    _shell32 = ctypes.windll.shell32
    _kernel32 = ctypes.windll.kernel32

    def _make_int_resource(res_id: int):
        return ctypes.cast(ctypes.c_void_p(res_id & 0xFFFF), wintypes.LPCWSTR)

    _kernel32.GetModuleHandleW.argtypes = [wintypes.LPCWSTR]
    _kernel32.GetModuleHandleW.restype = HINSTANCE
    _kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
    _kernel32.CreateMutexW.restype = HANDLE
    _kernel32.GetLastError.argtypes = []
    _kernel32.GetLastError.restype = wintypes.DWORD
    _kernel32.CloseHandle.argtypes = [HANDLE]
    _kernel32.CloseHandle.restype = wintypes.BOOL

    _user32.RegisterClassW.argtypes = [ctypes.POINTER(WNDCLASSW)]
    _user32.RegisterClassW.restype = ATOM
    _user32.UnregisterClassW.argtypes = [wintypes.LPCWSTR, HINSTANCE]
    _user32.UnregisterClassW.restype = wintypes.BOOL

    _user32.CreateWindowExW.argtypes = [
        wintypes.DWORD,
        wintypes.LPCWSTR,
        wintypes.LPCWSTR,
        wintypes.DWORD,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        HMENU,
        HINSTANCE,
        wintypes.LPVOID,
    ]
    _user32.CreateWindowExW.restype = wintypes.HWND

    _user32.LoadIconW.argtypes = [HINSTANCE, wintypes.LPCWSTR]
    _user32.LoadIconW.restype = HICON
    _user32.LoadImageW.argtypes = [
        HINSTANCE,
        wintypes.LPCWSTR,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.UINT,
    ]
    _user32.LoadImageW.restype = wintypes.HANDLE
    _user32.DestroyIcon.argtypes = [HICON]
    _user32.DestroyIcon.restype = wintypes.BOOL
    _user32.DestroyWindow.argtypes = [wintypes.HWND]
    _user32.DestroyWindow.restype = wintypes.BOOL
    _user32.DefWindowProcW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    _user32.DefWindowProcW.restype = LRESULT
    _user32.PostQuitMessage.argtypes = [ctypes.c_int]
    _user32.PostQuitMessage.restype = None
    _user32.PostMessageW.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    _user32.PostMessageW.restype = wintypes.BOOL

    _user32.GetMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT]
    _user32.GetMessageW.restype = ctypes.c_int
    _user32.TranslateMessage.argtypes = [ctypes.POINTER(MSG)]
    _user32.TranslateMessage.restype = wintypes.BOOL
    _user32.DispatchMessageW.argtypes = [ctypes.POINTER(MSG)]
    _user32.DispatchMessageW.restype = LRESULT

    _user32.CreatePopupMenu.argtypes = []
    _user32.CreatePopupMenu.restype = HMENU
    _user32.AppendMenuW.argtypes = [HMENU, wintypes.UINT, UINT_PTR, wintypes.LPCWSTR]
    _user32.AppendMenuW.restype = wintypes.BOOL
    _user32.TrackPopupMenu.argtypes = [
        HMENU,
        wintypes.UINT,
        ctypes.c_int,
        ctypes.c_int,
        ctypes.c_int,
        wintypes.HWND,
        LPCRECT,
    ]
    _user32.TrackPopupMenu.restype = UINT_PTR
    _user32.DestroyMenu.argtypes = [HMENU]
    _user32.DestroyMenu.restype = wintypes.BOOL
    _user32.GetCursorPos.argtypes = [ctypes.POINTER(POINT)]
    _user32.GetCursorPos.restype = wintypes.BOOL
    _user32.SetForegroundWindow.argtypes = [wintypes.HWND]
    _user32.SetForegroundWindow.restype = wintypes.BOOL
    _user32.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    _user32.FindWindowW.restype = wintypes.HWND
    _user32.IsIconic.argtypes = [wintypes.HWND]
    _user32.IsIconic.restype = wintypes.BOOL
    _user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
    _user32.ShowWindow.restype = wintypes.BOOL
    _user32.BringWindowToTop.argtypes = [wintypes.HWND]
    _user32.BringWindowToTop.restype = wintypes.BOOL

    _shell32.Shell_NotifyIconW.argtypes = [wintypes.DWORD, ctypes.POINTER(NOTIFYICONDATAW)]
    _shell32.Shell_NotifyIconW.restype = wintypes.BOOL
    _shell32.ExtractIconW.argtypes = [HINSTANCE, wintypes.LPCWSTR, wintypes.UINT]
    _shell32.ExtractIconW.restype = HICON
else:
    ctypes = None
    wintypes = None


def focus_existing_control_window(title: str) -> bool:
    """Try to bring the existing control window to foreground."""
    if sys.platform != "win32":
        return False
    hwnd = _user32.FindWindowW(None, title)
    if not hwnd:
        return False

    try:
        if _user32.IsIconic(hwnd):
            _user32.ShowWindow(hwnd, SW_RESTORE)
        else:
            _user32.ShowWindow(hwnd, SW_SHOW)
        _user32.BringWindowToTop(hwnd)
        _user32.SetForegroundWindow(hwnd)
    except Exception:
        return False
    return True


class SingleInstanceLock:
    """Cross-process single-instance lock on Windows."""

    def __init__(self, name: str) -> None:
        self.name = name
        self.handle = None

    def acquire(self) -> bool:
        if sys.platform != "win32":
            return True
        self.handle = _kernel32.CreateMutexW(None, False, self.name)
        if not self.handle:
            return False
        if _kernel32.GetLastError() == ERROR_ALREADY_EXISTS:
            _kernel32.CloseHandle(self.handle)
            self.handle = None
            return False
        return True

    def release(self) -> None:
        if sys.platform != "win32":
            return
        if self.handle:
            _kernel32.CloseHandle(self.handle)
            self.handle = None


class WinTrayIcon:
    """Windows notification area (system tray) icon."""

    WM_TRAYICON = 0x0400 + 201
    WM_COMMAND = 0x0111
    WM_CLOSE = 0x0010
    WM_DESTROY = 0x0002
    WM_LBUTTONUP = 0x0202
    WM_RBUTTONUP = 0x0205
    WM_CONTEXTMENU = 0x007B

    NIM_ADD = 0x00000000
    NIM_MODIFY = 0x00000001
    NIM_DELETE = 0x00000002
    NIF_MESSAGE = 0x00000001
    NIF_ICON = 0x00000002
    NIF_TIP = 0x00000004

    TPM_RETURNCMD = 0x0100
    TPM_NONOTIFY = 0x0080
    TPM_RIGHTBUTTON = 0x0002
    MF_BYPOSITION = 0x00000400
    MF_STRING = 0x00000000

    ID_TRAY_SHOW = 1001
    ID_TRAY_SETTINGS = 1002
    ID_TRAY_EXIT = 1003

    IDI_APPLICATION = 32512
    IDI_WARNING = 32515

    def __init__(
        self,
        tooltip: str,
        icon_path: Optional[str],
        on_show: Callable[[], None],
        on_settings: Callable[[], None],
        on_exit: Callable[[], None],
        logger: Callable[[str], None],
    ) -> None:
        self.tooltip = tooltip[:127]
        self.icon_path = icon_path
        self.on_show = on_show
        self.on_settings = on_settings
        self.on_exit = on_exit
        self.logger = logger

        self._thread: Optional[threading.Thread] = None
        self._ready = threading.Event()
        self._hwnd = None
        self._hinstance = None
        self._class_name = f"DesktopReminderTray_{os.getpid()}_{id(self)}"
        self._wndproc = None
        self._nid = None
        self._icon_handle = None
        self._owned_icon = False

    def start(self) -> bool:
        if sys.platform != "win32":
            self.logger("Tray icon is only supported on Windows.")
            return False
        self._thread = threading.Thread(target=self._thread_main, daemon=True)
        self._thread.start()
        self._ready.wait(timeout=3.0)
        return self._hwnd is not None

    def stop(self) -> None:
        if sys.platform != "win32":
            return
        if self._hwnd:
            _user32.PostMessageW(self._hwnd, self.WM_CLOSE, 0, 0)
        if self._thread and self._thread.is_alive() and threading.current_thread() != self._thread:
            self._thread.join(timeout=2.0)
        self._thread = None

    def update_tooltip(self, tooltip: str) -> bool:
        if sys.platform != "win32":
            return False
        self.tooltip = tooltip[:127]
        if self._nid is None:
            return False
        try:
            self._nid.szTip = self.tooltip
            previous_flags = self._nid.uFlags
            self._nid.uFlags = self.NIF_TIP
            ok = bool(_shell32.Shell_NotifyIconW(self.NIM_MODIFY, ctypes.byref(self._nid)))
            self._nid.uFlags = previous_flags
            if not ok:
                self.logger("Failed to update tray tooltip.")
            return ok
        except Exception:
            return False

    def _thread_main(self) -> None:
        self._hinstance = _kernel32.GetModuleHandleW(None)
        self._wndproc = WNDPROC(self._wnd_proc)

        wnd_class = WNDCLASSW()
        wnd_class.lpfnWndProc = self._wndproc
        wnd_class.hInstance = self._hinstance
        wnd_class.lpszClassName = self._class_name
        atom = _user32.RegisterClassW(ctypes.byref(wnd_class))
        if not atom:
            self.logger("Failed to register tray window class.")
            self._ready.set()
            return

        self._hwnd = _user32.CreateWindowExW(
            0,
            self._class_name,
            "DesktopReminderTrayWindow",
            0,
            0,
            0,
            0,
            0,
            None,
            None,
            self._hinstance,
            None,
        )
        if not self._hwnd:
            self.logger("Failed to create tray window.")
            _user32.UnregisterClassW(self._class_name, self._hinstance)
            self._ready.set()
            return

        hicon = self._load_icon_handle()
        if not hicon:
            self.logger("Failed to load tray icon handle.")
            _user32.DestroyWindow(self._hwnd)
            _user32.UnregisterClassW(self._class_name, self._hinstance)
            self._hwnd = None
            self._ready.set()
            return
        self._icon_handle = hicon
        self._nid = NOTIFYICONDATAW()
        self._nid.cbSize = ctypes.sizeof(NOTIFYICONDATAW)
        self._nid.hWnd = self._hwnd
        self._nid.uID = 1
        self._nid.uFlags = self.NIF_MESSAGE | self.NIF_ICON | self.NIF_TIP
        self._nid.uCallbackMessage = self.WM_TRAYICON
        self._nid.hIcon = self._icon_handle
        self._nid.szTip = self.tooltip

        ok = _shell32.Shell_NotifyIconW(self.NIM_ADD, ctypes.byref(self._nid))
        if not ok:
            self.logger("Failed to add tray icon.")
            _user32.DestroyWindow(self._hwnd)
            _user32.UnregisterClassW(self._class_name, self._hinstance)
            self._hwnd = None
            self._ready.set()
            return

        self._ready.set()
        self.logger("Tray icon started.")

        msg = MSG()
        while _user32.GetMessageW(ctypes.byref(msg), None, 0, 0) != 0:
            _user32.TranslateMessage(ctypes.byref(msg))
            _user32.DispatchMessageW(ctypes.byref(msg))

        if self._nid is not None:
            _shell32.Shell_NotifyIconW(self.NIM_DELETE, ctypes.byref(self._nid))
        if self._icon_handle and self._owned_icon:
            _user32.DestroyIcon(self._icon_handle)
            self._icon_handle = None
            self._owned_icon = False
        _user32.UnregisterClassW(self._class_name, self._hinstance)
        self._hwnd = None

    def _load_icon_handle(self):
        if self.icon_path:
            try:
                path = os.path.abspath(self.icon_path)
                if os.path.exists(path):
                    hicon = _user32.LoadImageW(
                        None,
                        path,
                        IMAGE_ICON,
                        0,
                        0,
                        LR_LOADFROMFILE | LR_DEFAULTSIZE,
                    )
                    if hicon:
                        self._owned_icon = True
                        return HICON(hicon)
                    self.logger(f"Failed to load tray icon from file: {path}")
            except Exception:
                self.logger("Unexpected error loading tray icon file.")

        # If frozen, try using the executable's embedded icon for consistency.
        if getattr(sys, "frozen", False):
            try:
                exe_path = os.path.abspath(sys.executable)
                if os.path.exists(exe_path):
                    hicon = _shell32.ExtractIconW(None, exe_path, 0)
                    icon_value = int(ctypes.cast(hicon, ctypes.c_void_p).value or 0)
                    if icon_value > 1:
                        self._owned_icon = True
                        return HICON(hicon)
            except Exception:
                pass

        # Final fallback to default application icon.
        self._owned_icon = False
        return _user32.LoadIconW(None, _make_int_resource(self.IDI_APPLICATION))

    def _show_context_menu(self) -> None:
        if not self._hwnd:
            return
        menu = _user32.CreatePopupMenu()
        if not menu:
            return
        _user32.AppendMenuW(menu, self.MF_BYPOSITION | self.MF_STRING, self.ID_TRAY_SHOW, "显示控制窗口")
        _user32.AppendMenuW(menu, self.MF_BYPOSITION | self.MF_STRING, self.ID_TRAY_SETTINGS, "设置")
        _user32.AppendMenuW(menu, self.MF_BYPOSITION | self.MF_STRING, self.ID_TRAY_EXIT, "退出程序")

        pt = POINT()
        _user32.GetCursorPos(ctypes.byref(pt))
        _user32.SetForegroundWindow(self._hwnd)
        cmd = _user32.TrackPopupMenu(
            menu,
            self.TPM_RETURNCMD | self.TPM_NONOTIFY | self.TPM_RIGHTBUTTON,
            pt.x,
            pt.y,
            0,
            self._hwnd,
            None,
        )
        _user32.DestroyMenu(menu)

        if cmd == self.ID_TRAY_SHOW:
            self.on_show()
        elif cmd == self.ID_TRAY_SETTINGS:
            self.on_settings()
        elif cmd == self.ID_TRAY_EXIT:
            self.on_exit()

    def _wnd_proc(self, hwnd, msg, wparam, lparam):
        if msg == self.WM_TRAYICON:
            event_code = int(lparam) & 0xFFFF
            if event_code == self.WM_LBUTTONUP:
                self.on_show()
            elif event_code in (self.WM_RBUTTONUP, self.WM_CONTEXTMENU):
                self._show_context_menu()
            return 0

        if msg == self.WM_COMMAND:
            command = int(wparam) & 0xFFFF
            if command == self.ID_TRAY_SHOW:
                self.on_show()
                return 0
            if command == self.ID_TRAY_SETTINGS:
                self.on_settings()
                return 0
            if command == self.ID_TRAY_EXIT:
                self.on_exit()
                return 0

        if msg == self.WM_CLOSE:
            _user32.DestroyWindow(hwnd)
            return 0

        if msg == self.WM_DESTROY:
            _user32.PostQuitMessage(0)
            return 0

        return _user32.DefWindowProcW(hwnd, msg, wparam, lparam)
