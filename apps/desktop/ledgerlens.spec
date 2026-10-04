# PyInstaller recipe for the LedgerLens desktop program.
#
# Build the web app first, then run from apps/api:
#   uv run pyinstaller ../desktop/ledgerlens.spec --noconfirm \
#       --distpath ../desktop/dist --workpath ../desktop/build
#
# Result: apps/desktop/dist/LedgerLens/ (LedgerLens.exe plus its libraries). The folder layout
# is deliberate: it starts faster than a single-file build and is what the installer packs.
from pathlib import Path

from PyInstaller.utils.hooks import collect_data_files, collect_submodules

HERE = Path(SPECPATH).resolve()  # apps/desktop
API = HERE.parent / "api"
WEB_DIST = HERE.parent / "web" / "dist"

if not (WEB_DIST / "index.html").is_file():
    raise SystemExit("Build the web app first: cd apps/web && npm ci && npm run build")

# Modules that are only imported by name at run time, which static analysis cannot see.
hiddenimports = (
    collect_submodules("uvicorn")
    + collect_submodules("anyio")
    + collect_submodules("alembic")
    + collect_submodules("sqlalchemy.dialects.sqlite")
    + collect_submodules("sqlalchemy.dialects.postgresql")
    + ["email_validator"]
)

# The migrations are loaded from files at run time, so they ship as data, not as bytecode.
alembic_dir = API / "alembic"
datas = [
    (str(path), str(Path("alembic") / path.parent.relative_to(alembic_dir)))
    for path in alembic_dir.rglob("*")
    if path.is_file() and "__pycache__" not in path.parts
]
datas += [(str(WEB_DIST), "web_dist")]
datas += collect_data_files("webview")

a = Analysis(
    [str(HERE / "entry.py")],
    pathex=[str(API)],
    datas=datas,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "mypy", "ruff"],
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="LedgerLens",
    console=False,  # a window program: no black console window
    icon=str(HERE / "ledgerlens.ico"),
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="LedgerLens", upx=False)
