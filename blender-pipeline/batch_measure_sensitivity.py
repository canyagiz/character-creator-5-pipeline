"""
batch_measure_sensitivity.py
Sensitivity probe FBX'lerini Blender ile oler, tek CSV cikarir.

Modlar:
  python batch_measure_sensitivity.py           # mevcut tum FBX'leri olc, cik
  python batch_measure_sensitivity.py --watch   # CC5 export ederken paralel izle (Ctrl+C ile dur)

Cikti: logs/sensitivity_measurements.csv
"""

import subprocess, sys, os, csv, json, time, argparse, signal

BLENDER_EXE  = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
SCRIPT       = os.path.join(os.path.dirname(__file__), "measure_anthropometry.py")
PROBE_CSV    = r"C:\Users\aliya\workspace\cc5-scripts\logs\sensitivity_probe.csv"
FBX_DIR      = r"C:\Users\aliya\workspace\cc5-scripts\fbx_export_sensitivity"
META_TMP_DIR = r"C:\Users\aliya\workspace\cc5-scripts\logs\sensitivity_meta"
OUT_CSV      = r"C:\Users\aliya\workspace\cc5-scripts\logs\sensitivity_measurements.csv"
POLL_SEC     = 10   # yeni FBX kontrol araligi (saniye)

os.makedirs(META_TMP_DIR, exist_ok=True)
os.makedirs(FBX_DIR, exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument("--watch", action="store_true",
                    help="CC5 export biterken paralel izle")
args = parser.parse_args()

# Probe CSV: char_id -> row
probe_rows = {}
with open(PROBE_CSV, encoding="utf-8") as f:
    for row in csv.DictReader(f):
        probe_rows[row["char_id"]] = row

# Mevcut sonuclari oku (resume destegi)
existing_results = {}
if os.path.exists(OUT_CSV):
    with open(OUT_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            existing_results[row["char_id"]] = row
    print(f"Resume: {len(existing_results)} onceki olcum bulundu")

def measure_fbx(fbx_path, char_id):
    meta_path = os.path.join(META_TMP_DIR, f"{char_id}_meta.json")
    r = subprocess.run(
        [BLENDER_EXE, "--background", "--python", SCRIPT,
         "--", fbx_path, META_TMP_DIR],
        capture_output=True, text=True
    )
    if r.returncode != 0 or not os.path.exists(meta_path):
        return None, r.stderr[-200:]
    with open(meta_path, encoding="utf-8") as f:
        return json.load(f), None

def build_row(char_id, meta):
    probe = probe_rows[char_id]
    return {
        "char_id":           char_id,
        "gender":            probe["gender"],
        "morph_key":         probe["morph_key"],
        "morph_id":          probe["morph_id"],
        "morph_value":       float(probe["morph_value"]),
        "height_cm":         meta.get("height_cm"),
        "shoulder_width_cm": meta.get("shoulder_width_cm"),
        "hip_width_cm":      meta.get("hip_width_cm"),
        "chest_circ_cm":     meta.get("chest_circ_cm"),
        "waist_circ_cm":     meta.get("waist_circ_cm"),
        "hip_circ_cm":       meta.get("hip_circ_cm"),
        "neck_circ_cm":      meta.get("neck_circ_cm"),
        "bicep_circ_cm":     meta.get("bicep_circ_cm"),
        "mid_thigh_circ_cm": meta.get("mid_thigh_circ_cm"),
        "calf_circ_cm":      meta.get("calf_circ_cm"),
    }

FIELDNAMES = [
    "char_id", "gender", "morph_key", "morph_id", "morph_value",
    "height_cm", "shoulder_width_cm", "hip_width_cm",
    "chest_circ_cm", "waist_circ_cm", "hip_circ_cm",
    "neck_circ_cm", "bicep_circ_cm", "mid_thigh_circ_cm", "calf_circ_cm",
]

def save_results(results):
    with open(OUT_CSV, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(results.values())

# ── Ana dongu ─────────────────────────────────────────────────────────────────
results  = dict(existing_results)
seen     = set(os.path.splitext(f)[0] for f in os.listdir(FBX_DIR) if f.endswith(".fbx"))
queue    = [c for c in seen if c in probe_rows and c not in results]
done = failed = 0
stop = False

def _sigint(sig, frame):
    global stop
    print("\nDurduruluyor — mevcut is bittikten sonra kapanir...")
    stop = True
signal.signal(signal.SIGINT, _sigint)

expected = len(probe_rows)
print(f"Probe: {expected} karakter | Mevcut FBX: {len(seen)} | Islenmemis: {len(queue)}")
if args.watch:
    print(f"Watch modu: her {POLL_SEC}s yeni FBX kontrol edilecek. Ctrl+C ile dur.")
print()

while not stop:
    # Kuyrugu isle
    while queue and not stop:
        char_id  = queue.pop(0)
        fbx_path = os.path.join(FBX_DIR, f"{char_id}.fbx")
        print(f"[{done+failed+1}] {char_id} ({probe_rows[char_id]['morph_key']}={probe_rows[char_id]['morph_value']}) ...",
              end=" ", flush=True)

        meta, err = measure_fbx(fbx_path, char_id)
        if meta is None:
            failed += 1
            print(f"HATA: {err}")
        else:
            results[char_id] = build_row(char_id, meta)
            done += 1
            sw = meta.get("shoulder_width_cm", "?")
            hw = meta.get("hip_width_cm", "?")
            print(f"OK  sh={sw} hip={hw}")

        # Her 20 olcumde kaydet
        if (done + failed) % 20 == 0:
            save_results(results)

    # Kuyruk bos
    if not args.watch:
        break

    # Watch: yeni FBX var mi?
    if stop:
        break
    time.sleep(POLL_SEC)
    new_fbx = [
        os.path.splitext(f)[0]
        for f in os.listdir(FBX_DIR)
        if f.endswith(".fbx")
    ]
    new_chars = [c for c in new_fbx if c not in seen and c in probe_rows and c not in results]
    if new_chars:
        print(f"[watcher] +{len(new_chars)} yeni FBX")
        queue.extend(new_chars)
        seen.update(new_chars)
    elif len(results) >= expected:
        print("Tum probe karakterleri olculdu, cikiliyor.")
        break

save_results(results)
print(f"\nBitti: {done} OK, {failed} hata | Toplam kayitli: {len(results)}")
print(f"Cikti: {OUT_CSV}")
if len(results) < expected:
    print(f"Eksik: {expected - len(results)} karakter henuz olculemedi")
    print("  Devam etmek icin tekrar calistir (resume otomatik)")
