"""Executable entry point. PyInstaller freezes this file into LedgerLens.exe."""

import multiprocessing

from app.desktop import main

if __name__ == "__main__":
    multiprocessing.freeze_support()
    raise SystemExit(main())
