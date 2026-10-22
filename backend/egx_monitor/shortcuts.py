"""Desktop icon + start-at-login, for Windows, macOS and Linux.

Used by `scripts/autostart.py` (running from source) and by the packaged EGX Monitor.exe,
which installs them on first run and removes them with `--uninstall-shortcuts`.
"""

from __future__ import annotations

import os
import platform
import plistlib
import subprocess
import sys
from pathlib import Path

from .config import FROZEN, RESOURCES

APP_NAME = "EGX Monitor"
BACKEND_DIR = Path(__file__).resolve().parents[1]
ICON_ICO = RESOURCES / "assets" / "icon.ico"
ICON_PNG = RESOURCES / "assets" / "icon.png"
PLIST = Path.home() / "Library" / "LaunchAgents" / "com.egxmonitor.app.plist"
# Hide the PowerShell console window that would otherwise flash on screen.
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


def _launch(windowless: bool) -> tuple[str, list[str], Path]:
    """(program, arguments, working directory) that starts the app."""
    if FROZEN:
        exe = Path(sys.executable)
        return str(exe), [], exe.parent
    python = Path(sys.executable)
    if windowless and os.name == "nt" and python.with_name("pythonw.exe").exists():
        python = python.with_name("pythonw.exe")
    return str(python), ["-m", "egx_monitor"], BACKEND_DIR


def _desktop() -> Path:
    if os.name == "nt":
        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"],
                text=True, creationflags=NO_WINDOW,
            ).strip()
            if out:
                return Path(out)
        except (OSError, subprocess.CalledProcessError):
            pass
    return Path.home() / "Desktop"


# ---------------------------------------------------------------- Windows
def _windows_paths() -> list[Path]:
    startup = Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"
    return [startup / f"{APP_NAME}.lnk", _desktop() / f"{APP_NAME}.lnk"]


def _install_windows() -> list[Path]:
    program, args, workdir = _launch(windowless=True)
    icon = program if FROZEN else str(ICON_ICO)  # the .exe carries the icon itself
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK);"
        "$s.TargetPath=$env:TARGET;$s.Arguments=$env:ARGS;$s.WorkingDirectory=$env:WORKDIR;"
        "$s.Description='Egyptian Exchange market monitor';$s.IconLocation=$env:ICON+',0';$s.Save()"
    )
    paths = _windows_paths()
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        env = {**os.environ, "LNK": str(path), "TARGET": program, "ARGS": " ".join(args), "WORKDIR": str(workdir), "ICON": icon}
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, env=env, creationflags=NO_WINDOW)
    return paths


# ---------------------------------------------------------------- macOS
def _macos_paths() -> list[Path]:
    return [PLIST, _desktop() / f"{APP_NAME}.command"]


def _install_macos() -> list[Path]:
    program, args, workdir = _launch(windowless=False)
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    with PLIST.open("wb") as f:
        plistlib.dump({"Label": "com.egxmonitor.app", "ProgramArguments": [program, *args],
                       "WorkingDirectory": str(workdir), "RunAtLoad": True}, f)
    cmd = _desktop() / f"{APP_NAME}.command"
    cmd.write_text(f'#!/bin/sh\ncd "{workdir}" && exec "{program}" {" ".join(args)}\n')
    cmd.chmod(0o755)
    return [PLIST, cmd]


# ---------------------------------------------------------------- Linux
def _linux_paths() -> list[Path]:
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return [config / "autostart" / "egx-monitor.desktop", _desktop() / "egx-monitor.desktop"]


def _install_linux() -> list[Path]:
    program, args, workdir = _launch(windowless=False)
    entry = (
        "[Desktop Entry]\nType=Application\n"
        f"Name={APP_NAME}\nComment=Egyptian Exchange market monitor\n"
        f'Exec=sh -c \'cd "{workdir}" && exec "{program}" {" ".join(args)}\'\n'
        f"Icon={ICON_PNG}\nTerminal=false\nCategories=Office;Finance;\nX-GNOME-Autostart-enabled=true\n"
    )
    paths = _linux_paths()
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(entry)
        p.chmod(0o755)
    return paths


# ---------------------------------------------------------------- public API
def _platform():
    return {
        "Windows": (_install_windows, _windows_paths),
        "Darwin": (_install_macos, _macos_paths),
    }.get(platform.system(), (_install_linux, _linux_paths))


def install() -> list[Path]:
    return _platform()[0]()


def uninstall() -> list[Path]:
    removed = []
    for p in _platform()[1]():
        if p.exists():
            p.unlink()
            removed.append(p)
    return removed
