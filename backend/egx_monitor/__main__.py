"""Start the dashboard: `python -m egx_monitor` (desktop window) or `--browser` / `--server-only`."""

from __future__ import annotations

import time

STARTED = time.perf_counter()  # measured before the heavier imports below

import argparse  # noqa: E402
import faulthandler  # noqa: E402
import logging  # noqa: E402
import os  # noqa: E402
import socket  # noqa: E402
import sys  # noqa: E402
import threading  # noqa: E402
import webbrowser  # noqa: E402

import uvicorn  # noqa: E402

from .config import FROZEN, PROJECT_ROOT, RESOURCES  # noqa: E402

APP_TITLE = "EGX Monitor"
ICON_ICO = RESOURCES / "assets" / "icon.ico"
ICON_PNG = RESOURCES / "assets" / "icon.png"
LOG_FILE = PROJECT_ROOT / "egx-monitor.log"

log = logging.getLogger("egx_monitor")


def step(name: str) -> None:
    """Startup timing, so a slow launch can be traced to one step (see egx-monitor.log)."""
    log.info("[startup %5.1fs] %s", time.perf_counter() - STARTED, name)


def _setup_logging() -> None:
    # pythonw (used by the desktop shortcut) has no console, so always log to a file too.
    handlers: list[logging.Handler] = [logging.FileHandler(LOG_FILE, mode="w", encoding="utf-8")]
    if sys.stderr:
        handlers.append(logging.StreamHandler())
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s", handlers=handlers)
    logging.getLogger("httpx").setLevel(logging.WARNING)
    # pywebview reports which browser engine it picks at DEBUG level; it reads this when imported.
    os.environ.setdefault("PYWEBVIEW_LOG", "debug")
    # A hard crash (e.g. inside the browser engine) still leaves a trace in the log.
    faulthandler.enable(file=handlers[0].stream)


def _watch_window_startup(log_stream) -> None:
    """If the window hasn't appeared after 20s, write every thread's stack to the log to show where it is stuck."""
    faulthandler.dump_traceback_later(20, repeat=False, file=log_stream)


def _window_shown() -> None:
    faulthandler.cancel_dump_traceback_later()
    import webview

    step(f"window shown (browser engine: {getattr(webview, 'renderer', None) or 'unknown'})")


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


def _first_run_shortcuts(settings) -> None:
    """Packaged .exe only: add the desktop icon + start-at-login once, in the background."""
    if not FROZEN or settings.shortcuts_installed:
        return

    def run() -> None:
        from . import shortcuts

        try:
            for path in shortcuts.install():
                log.info("created shortcut %s", path)
            settings.shortcuts_installed = True
            settings.save()
        except Exception as exc:
            log.warning("could not create shortcuts: %s", exc)

    threading.Thread(target=run, daemon=True).start()


def main() -> None:
    p = argparse.ArgumentParser(description="EGX Monitor dashboard")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--browser", action="store_true", help="open in the default browser instead of a desktop window")
    p.add_argument("--server-only", action="store_true", help="only run the API/web server (for development)")
    p.add_argument("--windowed", action="store_true", help="start as a normal window instead of maximized")
    p.add_argument("--install-shortcuts", action="store_true", help="add the desktop icon and start-at-login, then exit")
    p.add_argument("--uninstall-shortcuts", action="store_true", help="remove the desktop icon and start-at-login, then exit")
    args = p.parse_args()
    _setup_logging()
    step(f"Python started and imports loaded (log: {LOG_FILE})")

    if args.install_shortcuts or args.uninstall_shortcuts:
        from . import shortcuts

        for path in shortcuts.install() if args.install_shortcuts else shortcuts.uninstall():
            log.info("%s %s", "created" if args.install_shortcuts else "removed", path)
        return

    from .config import CONFIG_FILE
    from .server import app, settings

    step("dashboard server loaded")
    print(f"Settings file: {CONFIG_FILE}")

    port = _free_port(args.port)
    url = f"http://127.0.0.1:{port}/"
    # log_config=None: keep our logging setup (uvicorn would otherwise close the log file handler).
    # Explicit loop/http/ws so the packaged .exe doesn't depend on uvicorn's dynamic imports.
    config = uvicorn.Config(
        app, host="127.0.0.1", port=port, log_level="warning", log_config=None, loop="asyncio", http="h11", ws="none"
    )
    server = uvicorn.Server(config)

    if args.server_only:
        print(f"EGX Monitor API on {url}")
        server.run()
        return

    _first_run_shortcuts(settings)
    threading.Thread(target=server.run, daemon=True).start()
    _wait_until_up(port)
    step("local server is up")

    if not args.browser:
        try:
            import webview  # pywebview

            step("window library loaded")
            _windows_taskbar_identity()
            window = webview.create_window(
                APP_TITLE, url, width=1600, height=960, min_size=(1100, 700),
                maximized=not args.windowed, background_color="#0b0d10",
            )
            window.events.shown += _window_shown
            window.events.shown += _windows_set_icon
            window.events.loaded += lambda: step("dashboard page loaded")
            step("opening window")
            _watch_window_startup(logging.getLogger().handlers[0].stream)
            # On Windows the icon is set by _windows_set_icon. Never pass it to pywebview there: pywebview 6
            # hands it to .NET's Icon class, which rejects PNG data with an exception that kills the app.
            webview.start(**({} if os.name == "nt" else {"icon": str(ICON_PNG)}))
            faulthandler.cancel_dump_traceback_later()
            step("window closed")
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
