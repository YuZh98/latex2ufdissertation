"""--init: scaffold a new UF dissertation project."""

import shutil
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

from pipeline.types import ConverterError

BUNDLED_TEMPLATE_DIR = Path(__file__).parent / "template"
UF_IT_TEMPLATE_URL = (
    "https://it.ufl.edu/wp-content/uploads/2025/11/Dissertation___Thesis_Example_File.zip"
)
FETCH_TIMEOUT = 30  # seconds


def _fetch_remote(dest: Path) -> None:
    """Fetch the latest UF IT template zip and extract into dest."""
    req = urllib.request.Request(
        UF_IT_TEMPLATE_URL,
        headers={"User-Agent": "latex2ufdissertation"},
    )
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        data = resp.read()
    with zipfile.ZipFile(BytesIO(data)) as zf:
        zf.extractall(dest)
    entries = [p for p in dest.iterdir() if p.name not in ("__MACOSX",)]
    if len(entries) == 1 and entries[0].is_dir():
        inner = entries[0]
        for item in inner.iterdir():
            shutil.move(str(item), str(dest / item.name))
        inner.rmdir()


def _copy_bundled(dest: Path) -> None:
    for item in BUNDLED_TEMPLATE_DIR.iterdir():
        if item.is_dir():
            shutil.copytree(item, dest / item.name)
        else:
            shutil.copy2(item, dest / item.name)


def init_project(target: Path) -> None:
    """Scaffold a new UF dissertation project at `target`.

    Tries to fetch the latest UF IT template first; falls back to bundled.
    Refuses non-empty targets.
    """
    if target.exists() and any(target.iterdir()):
        raise ConverterError(f"target is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)

    try:
        _fetch_remote(target)
        print("  fetched latest template from UF IT")
    except Exception as e:
        print(f"  [warn] couldn't reach UF IT site ({type(e).__name__}); using bundled template")
        _copy_bundled(target)

    print(f"  scaffold ready at {target}/")
    print("  edit exampleMasterFile.tex to start writing.")
