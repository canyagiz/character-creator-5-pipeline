"""
pipeline.py — FBX → Render → Normal pipeline watcher

CC5'te batch_export çalışırken bu scripti ayrı bir terminalde başlat.
Yeni FBX dosyaları geldikçe render ve normal adımlarını otomatik tetikler.
Render ve normal paralel ilerler: render N'i işlerken normal N-1'i işler.

Restart güvenliği: her stage'in en son çıktısı --overwrite ile yeniden işlenir
(çökme anında yarım kalan dosya temizlenir).

Kullanım:
  python pipeline.py                # fbx_export/ izle, tümünü işle
  python pipeline.py --no-normal    # normal map adımını atla
  python pipeline.py --no-measure   # render'da ölçüm adımını atla
  python pipeline.py --poll 30      # FBX dizin kontrol aralığı (saniye, default 15)

Ctrl+C ile durdurulabilir — mevcut iş bittikten sonra temiz kapanır.
"""

import signal
import threading
import queue
import subprocess
import sys
import argparse
from pathlib import Path

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).resolve().parent
FBX_DIR       = BASE_DIR / "fbx_export"
SIL_DIR       = BASE_DIR / "renders" / "silhouettes"
NORMAL_DIR    = BASE_DIR / "renders" / "normal_maps"
RENDER_SCRIPT = BASE_DIR / "blender-pipeline" / "batch_render.py"
NORMAL_SCRIPT = BASE_DIR / "blender-pipeline" / "batch_normal.py"

SENTINEL = object()

# ── Args ───────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--no-normal",  action="store_true")
parser.add_argument("--no-measure", action="store_true")
parser.add_argument("--debug",      action="store_true")
parser.add_argument("--poll",       type=int, default=15)
parser.add_argument("--fbx-dir",    type=str, default=None,
                    help="FBX klasoru (default: fbx_export/)")
args = parser.parse_args()

if args.fbx_dir:
    FBX_DIR = Path(args.fbx_dir).resolve()

# ── Durum kontrolleri ──────────────────────────────────────────────────────────
def render_done(char_id: str) -> bool:
    return (SIL_DIR / char_id / f"{char_id}_front.png").exists()

def normal_done(char_id: str) -> bool:
    return (NORMAL_DIR / char_id / f"{char_id}_front.png").exists()

def run(script: Path, char_id: str, extra: tuple = ()) -> bool:
    r = subprocess.run([sys.executable, str(script), "--id", char_id, *extra])
    return r.returncode == 0

# ── Restart: en son dosyaları bul (çökmede yarım kalmış olabilirler) ──────────
def _last_by_mtime(directory: Path, glob: str) -> str | None:
    items = list(directory.glob(glob)) if directory.exists() else []
    return max(items, key=lambda p: p.stat().st_mtime).stem if items else None

def find_overwrite_sets() -> tuple[set, set]:
    """
    Restart'ta hangi char_id'lerin overwrite edilmesi gerektiğini döndürür.
    overwrite_render: render --overwrite ile çalışacak char'lar
    overwrite_normal: normal --overwrite ile çalışacak char'lar
    """
    last_fbx    = _last_by_mtime(FBX_DIR,    "*.fbx")   # export yarım kalmış olabilir
    last_render = _last_by_mtime(SIL_DIR,    "*/")       # render yarım kalmış olabilir
    last_normal = _last_by_mtime(NORMAL_DIR, "*/")       # normal yarım kalmış olabilir

    overwrite_render = {c for c in (last_fbx, last_render) if c}
    overwrite_normal = {c for c in (last_render, last_normal) if c}

    if overwrite_render or overwrite_normal:
        print("[pipeline] Restart overwrite listesi:")
        print(f"  render --overwrite : {sorted(overwrite_render) or '-'}")
        print(f"  normal --overwrite : {sorted(overwrite_normal) or '-'}")

    return overwrite_render, overwrite_normal

# ── FBX Watcher ────────────────────────────────────────────────────────────────
def fbx_watcher(render_q: queue.Queue, stop: threading.Event,
                overwrite_render: set):
    seen = set()

    # Başlangıçta mevcut FBX'leri tara
    for fbx in sorted(FBX_DIR.glob("*.fbx")):
        char_id = fbx.stem
        seen.add(char_id)
        overwrite = char_id in overwrite_render
        if overwrite or not render_done(char_id):
            render_q.put((char_id, overwrite))

    print(f"[watcher] {len(seen)} mevcut FBX, {render_q.qsize()} render bekliyor. İzleme başladı.")

    while not stop.is_set():
        stop.wait(args.poll)
        if stop.is_set():
            break
        for fbx in sorted(FBX_DIR.glob("*.fbx")):
            if fbx.stem not in seen:
                seen.add(fbx.stem)
                print(f"[watcher] ++ {fbx.stem}")
                render_q.put((fbx.stem, False))

    render_q.put(SENTINEL)
    print("[watcher] durduruldu")

# ── Render Worker ──────────────────────────────────────────────────────────────
def render_worker(render_q: queue.Queue, normal_q: queue.Queue,
                  overwrite_normal: set):
    measure_extra = ("--no-measure",) if args.no_measure else ()
    debug_extra   = ("--debug",)      if args.debug      else ()
    dir_extra     = ("--dir", str(FBX_DIR))

    while True:
        item = render_q.get()
        if item is SENTINEL:
            break

        char_id, overwrite = item
        if not overwrite and render_done(char_id):
            print(f"[render]  {char_id} | SKIP")
        else:
            extra = (("--overwrite",) if overwrite else ()) + measure_extra + debug_extra + dir_extra
            print(f"[render]  {char_id} | {'overwrite ' if overwrite else ''}başlıyor...")
            ok = run(RENDER_SCRIPT, char_id, extra)
            print(f"[render]  {char_id} | {'OK' if ok else 'HATA'}")
            if not ok:
                continue

        if not args.no_normal:
            ow_normal = char_id in overwrite_normal
            normal_q.put((char_id, ow_normal))

    normal_q.put(SENTINEL)
    print("[render]  worker bitti")

# ── Normal Worker ──────────────────────────────────────────────────────────────
def normal_worker(normal_q: queue.Queue):
    while True:
        item = normal_q.get()
        if item is SENTINEL:
            break

        char_id, overwrite = item
        if not overwrite and normal_done(char_id):
            print(f"[normal]  {char_id} | SKIP")
        else:
            extra = ("--overwrite",) if overwrite else ()
            print(f"[normal]  {char_id} | {'overwrite ' if overwrite else ''}başlıyor...")
            ok = run(NORMAL_SCRIPT, char_id, extra)
            print(f"[normal]  {char_id} | {'OK' if ok else 'HATA'}")

    print("[normal]  worker bitti")

# ── Main ───────────────────────────────────────────────────────────────────────
overwrite_render, overwrite_normal = find_overwrite_sets()

render_q = queue.Queue()
normal_q = queue.Queue()
stop     = threading.Event()

def _on_sigint(sig, frame):
    print("\n[pipeline] Durduruluyor — mevcut iş bitince kapanır (tekrar Ctrl+C: zorla çık)")
    if stop.is_set():
        sys.exit(1)
    stop.set()

signal.signal(signal.SIGINT, _on_sigint)

threads = [
    threading.Thread(target=fbx_watcher,  args=(render_q, stop, overwrite_render), name="watcher", daemon=False),
    threading.Thread(target=render_worker, args=(render_q, normal_q, overwrite_normal), name="render", daemon=False),
    threading.Thread(target=normal_worker, args=(normal_q,),                        name="normal", daemon=False),
]

for t in threads:
    t.start()
for t in threads:
    t.join()

print("[pipeline] Tamamlandı.")
