"""Pure Win32/ctypes helpers for the desktop GUI (P7b extraction).

The own-window lookup, window-icon set, taskbar flash, and fatal message box were
open-coded as scattered ctypes blocks inside `gui_api.GuiApi`. They are pure Win32 —
each takes an explicit window handle / icon path / message text and touches no GuiApi
state — so they live here as free functions with ZERO coupling to the bridge. gui_api
keeps the orchestration (the settings gate, the icon-path resolution, the find→set
polling, and all best-effort try/except + logging); these are the raw calls.

Windows-only by nature. Behavior-identical to the inline code they replaced.
"""
import ctypes
import os


def find_own_window(title):
    """The top-level window owned by THIS process with `title`, or None.

    FindWindowW(None, title) matches the FIRST window with that title across ALL
    processes -- another app, another instance, even an Explorer window named
    'TSMIS Exporter' -- so it could WM_SETICON the wrong process's window.
    Enumerating and matching on our own PID fixes that."""
    from ctypes import wintypes
    u32 = ctypes.windll.user32
    u32.GetWindowThreadProcessId.restype = wintypes.DWORD
    u32.GetWindowThreadProcessId.argtypes = [wintypes.HWND,
                                             ctypes.POINTER(wintypes.DWORD)]
    # Type the HWND-taking text calls too so a 64-bit handle is never
    # default-marshalled as a 32-bit int.
    u32.GetWindowTextLengthW.restype = ctypes.c_int
    u32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
    u32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
    my_pid = os.getpid()
    found = []

    @ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)
    def _cb(hwnd, _lparam):
        pid = wintypes.DWORD(0)
        u32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value != my_pid:
            return True
        n = u32.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        u32.GetWindowTextW(hwnd, buf, n + 1)
        if buf.value == title:
            found.append(hwnd)
            return False                          # stop enumerating
        return True

    u32.EnumWindows(_cb, 0)
    return found[0] if found else None


def set_window_icon(hwnd, ico_path):
    """WM_SETICON the small + big icons on `hwnd` from `ico_path` (a size that
    fails to load is skipped). Pure ctypes; the caller owns the window-found
    polling + logging."""
    from ctypes import wintypes
    u32 = ctypes.windll.user32
    u32.LoadImageW.restype = wintypes.HANDLE
    u32.SendMessageW.argtypes = [wintypes.HWND, wintypes.UINT,
                                 wintypes.WPARAM, wintypes.LPARAM]
    LR_LOADFROMFILE, IMAGE_ICON, WM_SETICON = 0x10, 1, 0x80
    for which, size in ((0, 16), (1, 32)):        # ICON_SMALL, ICON_BIG
        hicon = u32.LoadImageW(None, str(ico_path), IMAGE_ICON, size, size,
                               LR_LOADFROMFILE)
        if hicon:
            u32.SendMessageW(hwnd, WM_SETICON, which, hicon)


def flash_taskbar(hwnd):
    """Flash `hwnd`'s taskbar button until it is focused -- unless it is already
    the foreground window (then no-op). Pure ctypes; the caller owns the
    notify-on-finish gate + logging."""
    from ctypes import wintypes
    u32 = ctypes.windll.user32
    u32.GetForegroundWindow.restype = wintypes.HWND
    if u32.GetForegroundWindow() == hwnd:
        return                                    # already in front -- no nudge

    class FLASHWINFO(ctypes.Structure):
        _fields_ = [("cbSize", wintypes.UINT), ("hwnd", wintypes.HWND),
                    ("dwFlags", wintypes.DWORD), ("uCount", wintypes.UINT),
                    ("dwTimeout", wintypes.DWORD)]
    u32.FlashWindowEx.argtypes = [ctypes.POINTER(FLASHWINFO)]
    u32.FlashWindowEx.restype = wintypes.BOOL
    FLASHW_TRAY, FLASHW_TIMERNOFG = 0x2, 0xC       # taskbar; until focused
    info = FLASHWINFO(ctypes.sizeof(FLASHWINFO), hwnd,
                      FLASHW_TRAY | FLASHW_TIMERNOFG, 0, 0)
    u32.FlashWindowEx(ctypes.byref(info))


def message_box(text, title, flags=0x10):         # 0x10 = MB_ICONERROR
    """A modal Win32 MessageBox -- the last-resort error surface for a windowed
    .exe (no console, no window). The caller wraps it best-effort."""
    ctypes.windll.user32.MessageBoxW(0, text, title, flags)
