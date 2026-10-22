"""Add EGX Monitor to your desktop and start it automatically when you log in.

    python scripts/autostart.py install     # desktop shortcut + launch at login
    python scripts/autostart.py uninstall   # remove both

Run it with the Python from the project's virtualenv (the setup scripts do this for you)
so the shortcut launches the right interpreter. The packaged EGX Monitor.exe does this by itself.
"""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from egx_monitor import shortcuts  # noqa: E402


def main() -> None:
    action = sys.argv[1] if len(sys.argv) > 1 else "install"
    if action == "install":
        for p in shortcuts.install():
            print(f"created {p}")
        print(f"{shortcuts.APP_NAME} will now open when you log in. Double-click the desktop icon to open it any time.")
    elif action == "uninstall":
        for p in shortcuts.uninstall():
            print(f"removed {p}")
    else:
        sys.exit(__doc__)


if __name__ == "__main__":
    main()
