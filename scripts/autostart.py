"""Add EGX Monitor to your desktop and start it automatically when you log in.

    python scripts/autostart.py install     # desktop shortcut + launch at login
    python scripts/autostart.py uninstall   # remove both

Run it with the Python from the project's virtualenv (the setup scripts do this for you)
so the shortcut launches the right interpreter.
"""

from __future__ import annotations

import os
import platform
import plistlib
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
APP_NAME = "EGX Monitor"


def _python(windowless: bool) -> str:
    exe = Path(sys.executable)
    if windowless and os.name == "nt":
        pyw = exe.with_name("pythonw.exe")
        if pyw.exists():
            return str(pyw)
    return str(exe)


def _desktop() -> Path:
    if os.name == "nt":
        try:
            out = subprocess.check_output(
                ["powershell", "-NoProfile", "-Command", "[Environment]::GetFolderPath('Desktop')"], text=True
            ).strip()
            if out:
                return Path(out)
        except (OSError, subprocess.CalledProcessError):
            pass
    return Path.home() / "Desktop"


# ---------------------------------------------------------------- Windows
def _win_startup_dir() -> Path:
    return Path(os.environ["APPDATA"]) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Startup"


def _win_shortcut(path: Path) -> None:
    ps = (
        "$s=(New-Object -ComObject WScript.Shell).CreateShortcut($env:LNK);"
        "$s.TargetPath=$env:TARGET;$s.Arguments='-m egx_monitor';"
        "$s.WorkingDirectory=$env:WORKDIR;$s.Description='Egyptian Exchange market monitor';$s.Save()"
    )
    env = {**os.environ, "LNK": str(path), "TARGET": _python(windowless=True), "WORKDIR": str(BACKEND)}
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True, env=env)


def _install_windows() -> list[Path]:
    targets = [_win_startup_dir() / f"{APP_NAME}.lnk", _desktop() / f"{APP_NAME}.lnk"]
    for t in targets:
        t.parent.mkdir(parents=True, exist_ok=True)
        _win_shortcut(t)
    return targets


def _windows_paths() -> list[Path]:
    return [_win_startup_dir() / f"{APP_NAME}.lnk", _desktop() / f"{APP_NAME}.lnk"]


# ---------------------------------------------------------------- macOS
PLIST = Path.home() / "Library" / "LaunchAgents" / "com.egxmonitor.app.plist"


def _install_macos() -> list[Path]:
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    with PLIST.open("wb") as f:
        plistlib.dump({
            "Label": "com.egxmonitor.app",
            "ProgramArguments": [_python(False), "-m", "egx_monitor"],
            "WorkingDirectory": str(BACKEND),
            "RunAtLoad": True,
        }, f)
    cmd = _desktop() / f"{APP_NAME}.command"
    cmd.write_text(f'#!/bin/sh\ncd "{BACKEND}" && exec "{_python(False)}" -m egx_monitor\n')
    cmd.chmod(0o755)
    return [PLIST, cmd]


def _macos_paths() -> list[Path]:
    return [PLIST, _desktop() / f"{APP_NAME}.command"]


# ---------------------------------------------------------------- Linux
def _linux_entry() -> str:
    return (
        "[Desktop Entry]\nType=Application\n"
        f"Name={APP_NAME}\nComment=Egyptian Exchange market monitor\n"
        f'Exec=sh -c \'cd "{BACKEND}" && exec "{_python(False)}" -m egx_monitor\'\n'
        "Terminal=false\nCategories=Office;Finance;\nX-GNOME-Autostart-enabled=true\n"
    )


def _linux_paths() -> list[Path]:
    config = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
    return [config / "autostart" / "egx-monitor.desktop", _desktop() / "egx-monitor.desktop"]


def _install_linux() -> list[Path]:
    paths = _linux_paths()
    for p in paths:
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(_linux_entry())
        p.chmod(0o755)
    return paths


# ---------------------------------------------------------------- CLI
def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "install"
    system = platform.system()
    install, paths = {
        "Windows": (_install_windows, _windows_paths),
        "Darwin": (_install_macos, _macos_paths),
    }.get(system, (_install_linux, _linux_paths))

    if action == "install":
        for p in install():
            print(f"created {p}")
        print(f"{APP_NAME} will now open when you log in. Double-click the desktop icon to open it any time.")
    elif action == "uninstall":
        for p in paths():
            if p.exists():
                p.unlink()
                print(f"removed {p}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
