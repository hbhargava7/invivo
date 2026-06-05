#!/usr/bin/env python3
"""
setup_helvetica_neue.py
=======================
Make Helvetica Neue (all variants) available to matplotlib on macOS.

Why this exists
---------------
On macOS, Helvetica Neue ships ONLY as /System/Library/Fonts/HelveticaNeue.ttc
-- a read-only TrueType *collection* containing ~14 faces (UltraLight, Thin,
Light, Regular, Medium, Bold, their italics, and a couple of condensed cuts).

matplotlib.font_manager.addfont() reads only face index 0 of a collection, so
it can never see the variants. This script uses fonttools to split the .ttc
into individual .ttf files and writes them into a directory matplotlib scans
automatically, then clears the font cache so they're picked up for good.

Reproducibility
---------------
Helvetica Neue is proprietary; you may not redistribute the .ttf files. Commit
THIS SCRIPT to your repo instead. On any new Mac, activate your env and run it
again -- it regenerates the fonts from that machine's own system copy.

Usage
-----
    conda activate flowtx
    pip install fonttools            # one-time, if not already present
    python setup_helvetica_neue.py             # install into the active env
    python setup_helvetica_neue.py --user      # install into ~/Library/Fonts
    python setup_helvetica_neue.py --list       # just show what's registered
    python setup_helvetica_neue.py --ttc /path/to/HelveticaNeue.ttc
"""

from __future__ import annotations
import argparse
import os
import shutil
import sys
from pathlib import Path

# Standard macOS locations for the collection, in priority order.
DEFAULT_TTC_CANDIDATES = [
    "/System/Library/Fonts/HelveticaNeue.ttc",
    "/Library/Fonts/HelveticaNeue.ttc",
    str(Path.home() / "Library/Fonts/HelveticaNeue.ttc"),
]


def find_ttc(explicit: str | None) -> Path:
    """Locate the Helvetica Neue collection, or exit with a helpful message."""
    if explicit:
        p = Path(explicit).expanduser()
        if not p.exists():
            sys.exit(f"error: --ttc path does not exist: {p}")
        return p
    for cand in DEFAULT_TTC_CANDIDATES:
        if Path(cand).exists():
            return Path(cand)
    sys.exit(
        "error: could not find HelveticaNeue.ttc in any standard location.\n"
        "       Find it with:  ls /System/Library/Fonts | grep -i helvetica\n"
        "       then pass it explicitly with --ttc /path/to/HelveticaNeue.ttc"
    )


def target_dir(user_scope: bool) -> Path:
    """
    Where to write the extracted .ttf files.

    Default (env scope): matplotlib's own font dir inside the active conda env
    (.../site-packages/matplotlib/mpl-data/fonts/ttf). Auto-scanned, scoped to
    this env, and does NOT clutter Font Book. Re-run after a matplotlib upgrade.

    --user: ~/Library/Fonts. Survives env rebuilds/upgrades, but the faces show
    up system-wide (Font Book, other apps).
    """
    if user_scope:
        d = Path.home() / "Library/Fonts"
    else:
        import matplotlib
        d = Path(matplotlib.get_data_path()) / "fonts" / "ttf"
    d.mkdir(parents=True, exist_ok=True)
    return d


def extract_faces(ttc_path: Path, out_dir: Path) -> list[Path]:
    """Split the .ttc into individual .ttf files. Returns the written paths."""
    from fontTools.ttLib import TTCollection

    written: list[Path] = []
    collection = TTCollection(str(ttc_path))
    print(f"Opened {ttc_path.name}: {len(collection.fonts)} faces\n")

    for font in collection.fonts:
        name = font["name"]
        # Prefer the typographic family/subfamily (IDs 16/17); fall back to the
        # legacy family/subfamily (IDs 1/2). The full name (ID 4) is the label.
        family = name.getDebugName(16) or name.getDebugName(1) or "Unknown"
        subfamily = name.getDebugName(17) or name.getDebugName(2) or "Regular"
        full = name.getDebugName(4) or f"{family} {subfamily}"

        # Build a filesystem-safe filename, e.g. "HelveticaNeue-MediumItalic.ttf"
        slug = "".join(c for c in full if c.isalnum() or c in " -").strip()
        slug = slug.replace(" ", "")
        out_path = out_dir / f"{slug}.ttf"

        font.save(str(out_path))
        written.append(out_path)
        print(f"  + {full:38s} -> {out_path.name}")

    return written


def clear_cache() -> None:
    """Delete matplotlib's font cache so the new files get re-scanned."""
    import matplotlib

    cachedir = Path(matplotlib.get_cachedir())
    removed = []
    # Newer matplotlib uses fontlist-*.json; nuke the whole dir to be safe.
    if cachedir.exists():
        for item in cachedir.glob("fontlist-*.json"):
            item.unlink()
            removed.append(item.name)
    if removed:
        print(f"\nCleared font cache: {', '.join(removed)}")
    else:
        print("\nNo font cache files found (will build fresh on next import).")


def list_registered() -> None:
    """Rebuild the font manager and print every Helvetica face matplotlib sees."""
    # Import after cache clear so the manager rebuilds from disk.
    from matplotlib import font_manager

    rows = []
    for f in font_manager.fontManager.ttflist:
        if "helvetica neue" in f.name.lower():
            rows.append((f.name, str(f.weight), f.style, f.stretch))

    if not rows:
        print("\n(no Helvetica Neue faces visible to matplotlib yet)")
        return

    rows = sorted(set(rows))
    print("\nHelvetica Neue faces now visible to matplotlib")
    print("  family name                  | weight     | style   | stretch")
    print("  " + "-" * 64)
    for name, weight, style, stretch in rows:
        print(f"  {name:28s} | {weight:10s} | {style:7s} | {stretch}")
    print(
        "\nSelect a face like:\n"
        "    from matplotlib.font_manager import FontProperties\n"
        "    fp = FontProperties(family='Helvetica Neue', weight='medium')\n"
        "    ax.set_title('hello', fontproperties=fp)\n"
        "Use the exact 'family name' string above; some cuts (e.g. Condensed)\n"
        "register as their own family rather than a weight of 'Helvetica Neue'."
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ttc", help="explicit path to HelveticaNeue.ttc")
    ap.add_argument("--user", action="store_true",
                    help="install into ~/Library/Fonts instead of the conda env")
    ap.add_argument("--list", action="store_true",
                    help="skip extraction; just list what matplotlib sees")
    args = ap.parse_args()

    if args.list:
        list_registered()
        return

    ttc = find_ttc(args.ttc)
    out_dir = target_dir(args.user)
    print(f"Source : {ttc}")
    print(f"Target : {out_dir}\n")

    extract_faces(ttc, out_dir)
    clear_cache()
    list_registered()
    print("\nDone. Restart any running Python/Jupyter kernels to pick up changes.")


if __name__ == "__main__":
    main()
