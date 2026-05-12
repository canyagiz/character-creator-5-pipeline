"""
Deletes fbx_export and renders subfolders for IDs listed in missing_ids_ids_only.txt.

Usage:
  python delete_missing_ids.py            # dry-run (no actual deletion)
  python delete_missing_ids.py --delete   # actually delete
"""

import sys
import shutil
from pathlib import Path

DRY_RUN = "--delete" not in sys.argv

BASE = Path(__file__).parent
IDS_FILE = BASE / "missing_ids_ids_only.txt"
FBX_DIR = BASE / "fbx_export"
RENDERS_DIR = BASE / "renders"

ids = [line.strip() for line in IDS_FILE.read_text(encoding="utf-8").splitlines() if line.strip()]

if DRY_RUN:
    print("[DRY-RUN] Pass --delete to actually delete.\n")

deleted = []
not_found = []

for char_id in ids:
    targets = []

    fbx_folder = FBX_DIR / f"{char_id}.fbm"
    if fbx_folder.exists():
        targets.append(fbx_folder)

    meta_json = RENDERS_DIR / "meta" / f"{char_id}_meta.json"
    if meta_json.exists():
        targets.append(meta_json)

    for sub in RENDERS_DIR.iterdir():
        if not sub.is_dir():
            continue
        render_folder = sub / char_id
        if render_folder.exists():
            targets.append(render_folder)

    if not targets:
        not_found.append(char_id)
        continue

    for path in targets:
        print(f"{'[DRY-RUN] Would delete' if DRY_RUN else 'Deleting'}: {path}")
        if not DRY_RUN:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()
        deleted.append(path)

print(f"\n{'Would delete' if DRY_RUN else 'Deleted'}: {len(deleted)} folder(s)")
if not_found:
    print(f"Not found in any location ({len(not_found)}): {', '.join(not_found)}")
