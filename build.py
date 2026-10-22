"""Build a standalone executable for the current OS with PyInstaller (run: python build.py).

Needs: pip install pyinstaller pillow
The database and the emulator/ folder (FS-UAE, without the Kickstart ROMs) are copied next to the
app; the (large) game data folder is chosen by the user in Settings, or placed next to the app
as data/.
"""
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

NAME = "GamebaseAmiga"
separator = ";" if sys.platform == "win32" else ":"
args = [
    "gamebaseamiga.py",
    "--name", NAME,
    "--windowed",
    "--noconfirm",
    "--add-data", f"README.md{separator}.",
    "--add-data", f"images{separator}images",
]
if sys.platform != "darwin":  # Windows/Linux: single executable in dist/, next to the database
    args.append("--onefile")
PyInstaller.__main__.run(args)

# Ship the database and FS-UAE next to the app, where DataLayout looks for them. The Kickstart
# ROMs are copyrighted, so the folder is created empty: users add their own.
dist = Path("dist")
shutil.copy("gb_amiga_23.sqlite3", dist / "gb_amiga_23.sqlite3")
shutil.copytree("emulator", dist / "emulator", dirs_exist_ok=True,
                ignore=shutil.ignore_patterns("Kickstarts", "Cache", "Data", "Configurations",
                                              "Controllers", "Floppies", "Hard Drives",
                                              "CD-ROMs", "Save States", "Themes"))
(dist / "emulator" / "Kickstarts").mkdir(parents=True, exist_ok=True)
