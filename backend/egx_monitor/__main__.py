"""Start the dashboard: `python -m egx_monitor` (desktop window) or `--browser` / `--server-only`."""

from __future__ import annotations

import argparse
import logging
import socket
import threading
import time
import webbrowser

import uvicorn


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

            webview.create_window(
                "EGX Monitor", url, width=1600, height=960, min_size=(1100, 700),
                maximized=not args.windowed, background_color="#0b0d10",
            )
            webview.start()
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
