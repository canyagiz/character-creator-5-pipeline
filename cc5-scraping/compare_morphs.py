"""
compare_morphs.py — İki Morph Dictionary'yi karşılaştırır.

Kullanım:
  python compare_morphs.py

  - OTHER_PC : All_Detailed_Morph_Dictionary.txt  (öbür makineden scrape edildi)
  - THIS_PC  : This_PC_Morph_Dictionary.txt       (bu makinede scraper.py çalıştırınca üretilir)
"""

import re
from pathlib import Path

ROOT = Path(__file__).parent

OTHER_PC = ROOT / "All_Detailed_Morph_Dictionary.txt"
THIS_PC  = ROOT / "This_PC_Morph_Dictionary.txt"

CRITICAL_IDS = {
    # musc morphs
    "musc_abs":       "2025-05-08-15-26-33_embed_athetic_abs_iso_01",
    "musc_arm":       "2025-05-05-12-31-36_embed_athetic_arn_01",
    "musc_back":      "2025-05-05-12-31-03_embed_athetic_back_01",
    "musc_calf":      "2025-05-05-12-33-02_embed_athetic_calf_01",
    "musc_chest_a":   "2025-05-05-12-07-08_embed_athetic_chest_01",
    "musc_chest_b":   "2025-05-08-11-32-58_embed_athetic_chest_02",
    "musc_chest_c":   "2025-06-10-15-34-47_embed_athetic_chest_c",
    "musc_neck":      "2025-05-05-13-47-33_embed_athetic_chest_01",
    "musc_obliques":  "2025-05-08-15-29-44_embed_athetic_side_abs_01",
    "musc_shoulder":  "2025-05-05-12-22-16_embed_athetic_shoulder_01",
    "musc_thigh":     "2025-05-05-12-32-25_embed_athetic_thigh_01",
    "musc_waist":     "2025-05-05-12-18-34_embed_athetic_abs_01",
    # skin morphs
    "skin_abs":       "2025-05-07-13-43-26_pack_skinny_abs_01",
    "skin_arm":       "2025-05-07-14-12-07_pack_skinny_arm_01",
    "skin_back":      "2025-06-10-17-08-24_pack_skinny_back_02",
    "skin_buttocks":  "2025-06-10-17-01-51_pack_skinny_bottom_02",
    "skin_calf":      "2025-05-07-14-35-43_pack_skinny_calf_01",
    "skin_chest":     "2025-05-08-14-58-30_pack_skinny_chest_03",
    "skin_neck":      "2025-05-07-12-04-51_pack_skinny_neck_01",
    "skin_ribcage":   "2025-05-07-12-27-17_pack_skinny_rib_01",
    "skin_shoulder":  "2025-05-07-12-21-11_pack_skinny_shoulder_01",
    "skin_spine":     "2025-05-07-14-17-56_pack_skinny_spine_01",
    "skin_thigh":     "2025-06-10-17-18-17_pack_skinny_thigh_02",
}


def extract_ids(path: Path) -> set:
    ids = set()
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.search(r"Kod ID:\s*(.+?)\s*\|", line)
        if m:
            ids.add(m.group(1).strip())
    return ids


if not THIS_PC.exists():
    print(f"HATA: {THIS_PC} bulunamadi.")
    print("CC5 Script Editor'da scraper.py'i calistir, ciktisini")
    print(f"  {THIS_PC}")
    print("olarak kaydet, sonra bu scripti tekrar calistir.")
    raise SystemExit(1)

other_ids = extract_ids(OTHER_PC)
this_ids  = extract_ids(THIS_PC)

print(f"Öbür PC morph sayisi : {len(other_ids)}")
print(f"Bu PC morph sayisi   : {len(this_ids)}")
print()

# Pipeline'da kullanılan kritik morphların durumu
print("=== KRİTİK MORPH KONTROL (batch_export'ta kullanılanlar) ===")
missing_critical = []
for key, mid in sorted(CRITICAL_IDS.items()):
    status = "OK " if mid in this_ids else "EKSIK"
    print(f"  [{status}] {key:15s}  {mid}")
    if mid not in this_ids:
        missing_critical.append((key, mid))

print()
if missing_critical:
    print(f"!! {len(missing_critical)} kritik morph Bu PC'de YOK !!")
    print("Bu morphlar olmadan batch_export normal (default) ebatlar uretir.")
    print()
    print("Cozum: Obu PC'deki CC5 kurulumuna su HD morph paketleri aktarilmali:")
    for key, mid in missing_critical:
        print(f"  - {mid}")
else:
    print("Tum kritik morphlar Bu PC'de mevcut. Sorun baska bir yerde.")

# Öbür PC'de olan ama bu PC'de olmayan tüm morphlar
only_in_other = other_ids - this_ids
only_in_this  = this_ids  - other_ids

print()
print(f"=== GENEL FARK ===")
print(f"Sadece Öbür PC'de olan morph sayisi : {len(only_in_other)}")
print(f"Sadece Bu PC'de olan morph sayisi   : {len(only_in_this)}")

if only_in_other:
    out = ROOT / "missing_on_this_pc.txt"
    out.write_text("\n".join(sorted(only_in_other)), encoding="utf-8")
    print(f"Eksik morphlar yazildi: {out}")
