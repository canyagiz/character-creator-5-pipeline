"""
scraper_script_loader.py — v8
1) batch_export.py'yi dogrudan exec() ile calistirir (dialog yok)
2) CC5 plugin/startup dizinlerini bulur
"""

import RLPy
import os, sys

out = []
W = out.append

TARGET_SCRIPT = r"C:\Users\HP\character-creator-5-pipeline\props\batch_export.py"

# ── 1. RLPy path API'lerini sorgula ───────────────────────────────────────────
W("=" * 60)
W("CC5 PATH API")
W("=" * 60)
path_methods = [
    "GetProgramPath", "GetCustomDataPath", "GetCustomContentFolder",
    "GetDefaultContentFolder", "GetDefaultProjectPath",
    "GetTemplateDataPath", "GetCurrentProjectPath",
]
for m in path_methods:
    fn = getattr(RLPy.RApplication, m, None)
    if fn:
        try:
            W(f"  {m}() = {fn()}")
        except Exception as e:
            W(f"  {m}() = HATA: {e}")

# ── 2. Bilinen CC5 plugin dizinlerini kontrol et ─────────────────────────────
W("")
W("=" * 60)
W("PLUGIN DIZIN ARAMA")
W("=" * 60)
appdata   = os.environ.get("APPDATA", "")
localdata = os.environ.get("LOCALAPPDATA", "")
candidates = [
    os.path.join(appdata,   "Reallusion", "Character Creator 5"),
    os.path.join(appdata,   "Reallusion", "Character Creator 5", "Plugins"),
    os.path.join(appdata,   "Reallusion", "Character Creator 5", "Script"),
    os.path.join(appdata,   "Reallusion", "Character Creator 5", "Scripts"),
    os.path.join(localdata, "Reallusion", "Character Creator 5"),
    os.path.join(localdata, "Reallusion", "Character Creator 5", "Plugins"),
    r"C:\Program Files\Reallusion\Character Creator 5\Plugins",
    r"C:\Program Files\Reallusion\Character Creator 5\Script",
    r"C:\Program Files\Reallusion\Character Creator 5\Scripts",
]
for path in candidates:
    exists = os.path.isdir(path)
    W(f"  {'MEVCUT' if exists else 'yok   '} {path}")
    if exists:
        try:
            contents = os.listdir(path)
            for f in contents[:10]:
                W(f"    - {f}")
        except Exception:
            pass

# ── 3. sys.path'i goster (CC5 neyi import edebiliyor) ────────────────────────
W("")
W("=" * 60)
W("SYS.PATH")
W("=" * 60)
for p in sys.path:
    W(f"  {p}")

# ── 4. Dogrudan exec() ile batch_export.py calistir ─────────────────────────
W("")
W("=" * 60)
W("EXEC TEST")
W("=" * 60)
W(f"  exec({TARGET_SCRIPT}) baslatiliyor...")
print("\n".join(out))

exec(open(TARGET_SCRIPT, encoding="utf-8").read())
