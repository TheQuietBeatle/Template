"""Start the dashboard: `python -m egx_monitor` (desktop window) or `--browser` / `--server-only`."""

from __future__ import annotations

import argparse
import logging
import os
import socket
import threading
import time
import webbrowser

import uvicorn

from .config import PROJECT_ROOT

APP_TITLE = "EGX Monitor"
ICON_ICO = PROJECT_ROOT / "assets" / "icon.ico"
ICON_PNG = PROJECT_ROOT / "assets" / "icon.png"

def _free_port(preferred: int) -> int:
    with socket.socket() as s:
        try:
            s.bind(("127.0.0.1", preferred))
            return preferred
        except OSError:
            s.bind(("127.0.0.1", 0))
            return s.getsockname()[1]


def _wait_until_up(port: int, timeout: float = 15) -> None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                return
        except OSError:
            time.sleep(0.1)


def _windows_taskbar_identity() -> None:
    """Give the app its own taskbar entry, instead of being grouped under Python."""
    if os.name != "nt":
        return
    import ctypes

    try:
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("EGXMonitor.Desktop")
    except (AttributeError, OSError):
        pass


def _windows_set_icon() -> None:
    """Swap the window/taskbar icon from Python's to assets/icon.ico (called once the window is shown)."""
    if os.name != "nt" or not ICON_ICO.exists():
        return
    import ctypes

    user32 = ctypes.windll.user32
    user32.FindWindowW.restype = ctypes.c_void_p
    user32.LoadImageW.restype = ctypes.c_void_p
    user32.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_void_p, ctypes.c_void_p]
    hwnd = user32.FindWindowW(None, APP_TITLE)
    if not hwnd:
        return
    IMAGE_ICON, LR_LOADFROMFILE, WM_SETICON = 1, 0x10, 0x80
    for kind, size in ((0, 16), (1, 32)):  # ICON_SMALL, ICON_BIG
        icon = user32.LoadImageW(None, str(ICON_ICO), IMAGE_ICON, size, size, LR_LOADFROMFILE)
        if icon:
            user32.SendMessageW(hwnd, WM_SETICON, kind, icon)


def main() -> None:
    p = argparse.ArgumentParser(description="EGX Monitor dashboard")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--browser", action="store_true", help="open in the default browser instead of a desktop window")
    p.add_argument("--server-only", action="store_true", help="only run the API/web server (for development)")
    p.add_argument("--windowed", action="store_true", help="start as a normal window instead of maximized")
    args = p.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    from .config import CONFIG_FILE

    print(f"Settings file: {CONFIG_FILE}")

    port = _free_port(args.port)
    url = f"http://127.0.0.1:{port}/"
    config = uvicorn.Config("egx_monitor.server:app", host="127.0.0.1", port=port, log_level="warning")
    server = uvicorn.Server(config)

    if args.server_only:
        print(f"EGX Monitor API on {url}")
        server.run()
        return

    threading.Thread(target=server.run, daemon=True).start()
    _wait_until_up(port)

    if not args.browser:
        try:
            import webview  # pywebview

            _windows_taskbar_identity()
            window = webview.create_window(
                APP_TITLE, url, width=1600, height=960, min_size=(1100, 700),
                maximized=not args.windowed, background_color="#0b0d10",
            )
            window.events.shown += _windows_set_icon
            # `icon` is used by the GTK/Qt backends (Linux); Windows is handled by _windows_set_icon.
            webview.start(icon=str(ICON_PNG))
            server.should_exit = True
            return
        except Exception as exc:  # pywebview missing or no GUI backend
            logging.warning("Desktop window unavailable (%s); opening the browser instead.", exc)

    webbrowser.open(url)
    print(f"EGX Monitor running at {url} — press Ctrl+C to quit.")
    try:
        while True:
            time.sleep(3600)
    except KeyboardInterrupt:
        server.should_exit = True


if __name__ == "__main__":
    main()
