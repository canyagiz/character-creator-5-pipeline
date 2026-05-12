"""
renders/ klasöründeki dosyalar içinde renders.zip'te bulunmayanları
renders_2/ klasörüne taşır (klasör yapısını koruyarak).

Kullanım:
  python split_renders.py
  python split_renders.py --zip renders.zip --src renders --dst renders_2
"""

import argparse
import shutil
import zipfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", default="renders.zip")
    parser.add_argument("--src", default="renders")
    parser.add_argument("--dst", default="renders_2")
    args = parser.parse_args()

    zip_path = Path(args.zip)
    src_dir = Path(args.src)
    dst_dir = Path(args.dst)

    if not zip_path.exists():
        raise FileNotFoundError(f"ZIP bulunamadı: {zip_path}")
    if not src_dir.exists():
        raise FileNotFoundError(f"Kaynak klasör bulunamadı: {src_dir}")

    # ZIP içindeki dosyaları normalize edilmiş göreceli yollarla topla.
    # ZIP yolları "renders/sub/file.png" formatında — baştaki "renders/" kısmını çıkar.
    zip_prefix = src_dir.name + "/"
    zipped_files: set[str] = set()

    print(f"ZIP okunuyor: {zip_path} ...", flush=True)
    with zipfile.ZipFile(zip_path, "r") as zf:
        for entry in zf.infolist():
            name = entry.filename.replace("\\", "/")
            if entry.is_dir():
                continue
            # Eğer ZIP içi yol "renders/..." ile başlıyorsa başını at
            if name.startswith(zip_prefix):
                name = name[len(zip_prefix):]
            zipped_files.add(name)

    print(f"ZIP'te {len(zipped_files):,} dosya var.", flush=True)

    # Kaynak klasörü tara; ZIP'te olmayan dosyaları taşı
    moved = 0
    skipped = 0

    src_files = [f for f in src_dir.rglob("*") if f.is_file()]
    print(f"Kaynak klasörde {len(src_files):,} dosya bulundu. Filtreleniyor...", flush=True)

    for src_file in src_files:
        rel = src_file.relative_to(src_dir).as_posix()  # örn. "raw/char_00000/front.png"

        if rel in zipped_files:
            skipped += 1
            continue

        dst_file = dst_dir / rel
        dst_file.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(src_file), str(dst_file))
        moved += 1

        if moved % 500 == 0:
            print(f"  Taşındı: {moved:,}", flush=True)

    print(f"\nTamamlandı.")
    print(f"  Taşınan  : {moved:,} dosya → {dst_dir}/")
    print(f"  Atlanan  : {skipped:,} dosya (ZIP'te mevcut)")


if __name__ == "__main__":
    main()
