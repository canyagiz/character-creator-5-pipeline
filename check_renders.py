"""
check_renders.py — renders/ altındaki eksik dosyaları tespit eder.

Kontrol edilen klasörler:
  renders/meta/              — <char_id>_meta.json  (1 dosya/karakter)
  renders/raw/<char_id>/     — 8 PNG
  renders/normal_maps/<char_id>/ — 8 PNG
  renders/segmentation/<char_id>/ — 8 PNG
  renders/silhouettes/<char_id>/  — 8 PNG

Kullanım:
  python check_renders.py
  python check_renders.py --renders-dir D:/data/renders
  python check_renders.py --out missing_ids.txt
"""

import argparse
from pathlib import Path

VIEWS = [
    "front", "front_right", "right", "back_right",
    "back",  "back_left",   "left",  "front_left",
]

IMAGE_FOLDERS = ["raw", "normal_maps", "segmentation", "silhouettes"]

parser = argparse.ArgumentParser()
parser.add_argument(
    "--renders-dir",
    default=str(Path(__file__).resolve().parent / "renders"),
    help="renders/ kök klasörü (varsayılan: script yanındaki renders/)",
)
parser.add_argument(
    "--out",
    default="missing_ids.txt",
    help="Çıktı txt dosyası (varsayılan: missing_ids.txt)",
)
args = parser.parse_args()

renders = Path(args.renders_dir)
meta_dir = renders / "meta"

# ── Tüm char_id'leri topla ────────────────────────────────────────────────────
char_ids: set[str] = set()

if meta_dir.exists():
    for f in meta_dir.iterdir():
        if f.suffix == ".json" and f.name.endswith("_meta.json"):
            char_ids.add(f.name[: -len("_meta.json")])

for folder in IMAGE_FOLDERS:
    folder_path = renders / folder
    if folder_path.exists():
        for d in folder_path.iterdir():
            if d.is_dir():
                char_ids.add(d.name)

if not char_ids:
    print(f"Hiç karakter bulunamadı: {renders}")
    raise SystemExit(1)

all_ids = sorted(char_ids)
print(f"Toplam karakter: {len(all_ids)}")

# ── Eksik kontrol ─────────────────────────────────────────────────────────────
missing: dict[str, list[str]] = {}  # char_id -> eksik dosya açıklamaları

for char_id in all_ids:
    problems: list[str] = []

    # meta JSON
    meta_path = meta_dir / f"{char_id}_meta.json"
    if not meta_path.exists():
        problems.append("meta json")

    # 8-PNG klasörleri
    for folder in IMAGE_FOLDERS:
        char_dir = renders / folder / char_id
        if not char_dir.exists():
            problems.append(f"{folder}/ klasörü yok")
        else:
            for view in VIEWS:
                png = char_dir / f"{char_id}_{view}.png"
                if not png.exists():
                    problems.append(f"{folder}/{view}.png")

    if problems:
        missing[char_id] = problems

# ── Sonuç ─────────────────────────────────────────────────────────────────────
out_path = Path(args.out)
with out_path.open("w", encoding="utf-8") as f:
    f.write(f"# Eksik render/veri — {len(missing)} karakter\n")
    f.write(f"# renders: {renders}\n\n")
    for char_id, problems in sorted(missing.items()):
        f.write(f"{char_id}\n")
        for p in problems:
            f.write(f"  - {p}\n")

print(f"Eksik karakter sayısı : {len(missing)} / {len(all_ids)}")
print(f"Rapor kaydedildi      : {out_path.resolve()}")

if missing:
    ids_only_path = out_path.with_stem(out_path.stem + "_ids_only")
    with ids_only_path.open("w", encoding="utf-8") as f:
        f.write("\n".join(sorted(missing.keys())))
    print(f"Sadece ID listesi     : {ids_only_path.resolve()}")