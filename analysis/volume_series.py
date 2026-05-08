"""
volume_series.py
Verilen morph_key serisindeki tum FBX'lerin hacmini hesaplar.

Kullanim:
  python analysis/volume_series.py body_fat
  python analysis/volume_series.py body_fat --gender f
  python analysis/volume_series.py musc_waist --gender m
"""

import subprocess, os, json, tempfile, argparse
import pandas as pd

BLENDER_EXE   = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
VOLUME_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "blender-pipeline", "volume_probe.py")
FBX_DIR       = os.path.join(os.path.dirname(__file__), "..", "fbx_export_sensitivity")
MEAS_CSV      = os.path.join(os.path.dirname(__file__), "..", "logs", "sensitivity_measurements.csv")
LOG_DIR       = os.path.join(os.path.dirname(__file__), "..", "logs")

parser = argparse.ArgumentParser()
parser.add_argument("morph_key", help="CSV'deki morph_key degeri (orn: body_fat)")
parser.add_argument("--gender", default=None, choices=["f", "m"], help="f veya m (default: ikisi de)")
args = parser.parse_args()

df = pd.read_csv(MEAS_CSV)
mask = df["morph_key"] == args.morph_key
if args.gender:
    mask &= df["gender"] == ("female" if args.gender == "f" else "male")
rows = df[mask].sort_values(["gender", "morph_value"]).reset_index(drop=True)

if rows.empty:
    print(f"No rows found for morph_key='{args.morph_key}'")
    raise SystemExit(1)

print(f"morph_key={args.morph_key}  rows={len(rows)}\n")

tmp_dir = tempfile.mkdtemp()
results = []

for _, row in rows.iterrows():
    char_id  = row["char_id"]
    fbx_path = os.path.join(FBX_DIR, f"{char_id}.fbx")
    out_json = os.path.join(tmp_dir, f"{char_id}_vol.json")

    if not os.path.exists(fbx_path):
        print(f"  SKIP (no FBX): {char_id}")
        continue

    proc = subprocess.run(
        [BLENDER_EXE, "--background", "--python", VOLUME_SCRIPT,
         "--", fbx_path, out_json],
        capture_output=True, text=True
    )
    if proc.returncode != 0 or not os.path.exists(out_json):
        print(f"  ERROR: {char_id}")
        print(proc.stderr[-300:])
        continue

    with open(out_json) as f:
        vol = json.load(f)["volume_L"]

    waist = row.get("waist_circ_cm", float("nan"))
    chest = row.get("chest_circ_cm", float("nan"))
    hip   = row.get("hip_circ_cm",   float("nan"))

    results.append({
        "char_id":      char_id,
        "gender":       row["gender"],
        "morph_value":  row["morph_value"],
        "waist_cm":     waist,
        "chest_cm":     chest,
        "hip_cm":       hip,
        "volume_L":     round(vol, 4),
    })

    print(f"  {char_id:30s}  morph={row['morph_value']:.1f}  "
          f"waist={waist:6.2f}cm  vol={vol:7.3f} L")

out_df  = pd.DataFrame(results)
tag     = args.morph_key + (f"_{args.gender}" if args.gender else "")
out_csv = os.path.join(LOG_DIR, f"volume_{tag}.csv")
out_df.to_csv(out_csv, index=False)

print(f"\n--- Summary ---")
print(out_df[["gender", "morph_value", "waist_cm", "volume_L"]].to_string(index=False))

if len(out_df) > 1:
    corr = out_df["waist_cm"].corr(out_df["volume_L"])
    dv   = out_df["volume_L"].max() - out_df["volume_L"].min()
    print(f"\nVolume range : {out_df['volume_L'].min():.3f} - {out_df['volume_L'].max():.3f} L  (delta={dv:.3f} L)")
    print(f"Waist range  : {out_df['waist_cm'].min():.2f} - {out_df['waist_cm'].max():.2f} cm")
    print(f"Pearson r    : {corr:.4f}")

print(f"\nSaved: {out_csv}")
