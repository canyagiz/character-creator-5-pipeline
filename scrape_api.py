import RLPy
from pathlib import Path

_ROOT = Path(__file__).resolve().parent

OUTPUT = str(_ROOT / "cc5-scraping" / "Full_API_Dump.txt")

def get_members(obj):
    return [m for m in dir(obj) if not m.startswith("__")]

with open(OUTPUT, "w", encoding="utf-8") as f:

    # 1. RLPy modülünün tüm üst-düzey isimleri
    top = get_members(RLPy)
    f.write("=== RLPy TOP-LEVEL ===\n")
    for name in top:
        f.write(f"{name}\n")

    # 2. Export/File/Scene/Global ile ilgili görünen sınıfları derinlemesine tara
    keywords = ["export", "file", "scene", "global", "render", "project",
                "application", "save", "fbx", "obj", "camera", "light"]

    f.write("\n\n=== DETAYLI SINIF TARAMAS ===\n")
    for name in top:
        if any(kw in name.lower() for kw in keywords):
            obj = getattr(RLPy, name)
            members = get_members(obj)
            f.write(f"\n--- {name} ---\n")
            for m in members:
                f.write(f"  {m}\n")

    # 3. RScene ve RGlobal her zaman önemli
    for cls_name in ["RScene", "RGlobal", "RApplication", "RFileService"]:
        if hasattr(RLPy, cls_name):
            obj = getattr(RLPy, cls_name)
            f.write(f"\n--- {cls_name} ---\n")
            for m in get_members(obj):
                f.write(f"  {m}\n")

print("Done:", OUTPUT)
