"""--init: scaffold a new UF dissertation project."""

import shutil
import sys
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

from latex2ufdissertation.pipeline.resolve import _safe_extract
from latex2ufdissertation.pipeline.types import ConverterError

BUNDLED_TEMPLATE_DIR = Path(__file__).parent / "template"
UF_IT_TEMPLATE_URL = "https://it.ufl.edu/helpdesk/media/itufledu/tampd-graduate-resources-/Dissertation___Thesis_Example_File.zip"
FETCH_TIMEOUT = 30  # seconds
FETCH_MAX_BYTES = 50 * 1024 * 1024  # 50 MB cap on remote template download


def _fetch_remote(dest: Path) -> None:
    """Fetch the latest UF IT template zip and extract into dest."""
    req = urllib.request.Request(
        UF_IT_TEMPLATE_URL,
        headers={"User-Agent": "latex2ufdissertation"},
    )
    with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:
        data = resp.read(FETCH_MAX_BYTES + 1)

    if len(data) > FETCH_MAX_BYTES:
        raise ConverterError(f"remote template too large (> {FETCH_MAX_BYTES // (1024 * 1024)} MB)")

    with zipfile.ZipFile(BytesIO(data)) as zf:
        _safe_extract(zf, dest)

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
        print("  fetched latest template from UF IT", file=sys.stderr)
    except Exception as e:
        print(
            f"  [warn] couldn't reach UF IT site ({type(e).__name__}); using bundled template",
            file=sys.stderr,
        )
        _copy_bundled(target)

    print(f"  scaffold ready at {target}/", file=sys.stderr)
    print("  edit exampleMasterFile.tex to start writing.", file=sys.stderr)
