"""
patch_volume_meta.py
Mevcut meta.json'larda volume_L yoksa FBX'ten hesaplayip ekler.

Calistir: python patch_volume_meta.py
Secenekler:
  --overwrite   volume_L zaten varsa bile yeniden hesapla
  --dry-run     neyin guncelleneceğini goster, dosya yazma
"""

import subprocess, os, json, tempfile, argparse

BLENDER_EXE   = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
VOLUME_SCRIPT = os.path.join(os.path.dirname(__file__), "blender-pipeline", "volume_probe.py")
META_DIR      = os.path.join(os.path.dirname(__file__), "logs", "sensitivity_meta")
FBX_DIR       = os.path.join(os.path.dirname(__file__), "fbx_export_sensitivity")

parser = argparse.ArgumentParser()
parser.add_argument("--overwrite", action="store_true")
parser.add_argument("--dry-run",   action="store_true")
args = parser.parse_args()

meta_files = sorted(f for f in os.listdir(META_DIR) if f.endswith("_meta.json"))
tmp_dir    = tempfile.mkdtemp()

done = skipped = failed = 0

for fname in meta_files:
    meta_path = os.path.join(META_DIR, fname)
    char_id   = fname.replace("_meta.json", "")
    fbx_path  = os.path.join(FBX_DIR, f"{char_id}.fbx")

    with open(meta_path, encoding="utf-8") as f:
        meta = json.load(f)

    if "volume_L" in meta and not args.overwrite:
        skipped += 1
        continue

    if not os.path.exists(fbx_path):
        print(f"  SKIP (no FBX): {char_id}")
        skipped += 1
        continue

    if args.dry_run:
        print(f"  [dry-run] would patch: {char_id}")
        done += 1
        continue

    out_json = os.path.join(tmp_dir, f"{char_id}_vol.json")
    proc = subprocess.run(
        [BLENDER_EXE, "--background", "--python", VOLUME_SCRIPT,
         "--", fbx_path, out_json],
        capture_output=True, text=True
    )
    if proc.returncode != 0 or not os.path.exists(out_json):
        print(f"  ERROR: {char_id}")
        print(proc.stderr[-200:])
        failed += 1
        continue

    with open(out_json) as f:
        volume_L = json.load(f)["volume_L"]

    meta["volume_L"] = round(volume_L, 4)
    with open(meta_path, "w", encoding="utf-8") as f:
        json.dump(meta, f, indent=2)

    done += 1
    print(f"  {char_id:40s}  {volume_L:.3f} L")

print(f"\nDone: {done} patched, {skipped} skipped, {failed} failed")
