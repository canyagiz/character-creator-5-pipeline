"""
volume_vs_waist.py
musc_waist serisindeki FBX'lerin mesh hacmini hesaplar,
CSV'deki waist_circ_cm ile karşılaştırır ve grafik üretir.

Çalıştır: python analysis/volume_vs_waist.py
"""

import subprocess
import os
import json
import tempfile
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

BLENDER_EXE   = r"C:\Program Files\Blender Foundation\Blender 4.5\blender.exe"
VOLUME_SCRIPT = os.path.join(os.path.dirname(__file__), "..", "blender-pipeline", "volume_probe.py")
FBX_DIR       = os.path.join(os.path.dirname(__file__), "..", "fbx_export_sensitivity")
MEAS_CSV      = os.path.join(os.path.dirname(__file__), "..", "logs", "sensitivity_measurements.csv")
OUT_DIR       = os.path.join(os.path.dirname(__file__), "..", "analysis")

# ── CSV'den musc_waist satırlarını al ─────────────────────────────────────────
df = pd.read_csv(MEAS_CSV)
waist_df = df[df["morph_key"] == "musc_waist"].copy()
waist_df = waist_df.sort_values("morph_value").reset_index(drop=True)

print(f"musc_waist rows: {len(waist_df)}")
print(waist_df[["char_id", "morph_value", "waist_circ_cm"]].to_string(index=False))
print()

# ── Her FBX için hacim hesapla ────────────────────────────────────────────────
volumes = []
tmp_dir = tempfile.mkdtemp()

for _, row in waist_df.iterrows():
    char_id  = row["char_id"]
    fbx_path = os.path.join(FBX_DIR, f"{char_id}.fbx")
    out_json = os.path.join(tmp_dir, f"{char_id}_vol.json")

    if not os.path.exists(fbx_path):
        print(f"  SKIP (no FBX): {fbx_path}")
        volumes.append(None)
        continue

    print(f"  Processing: {char_id} ...", end=" ", flush=True)
    result = subprocess.run(
        [BLENDER_EXE, "--background", "--python", VOLUME_SCRIPT,
         "--", fbx_path, out_json],
        capture_output=True, text=True
    )

    if result.returncode != 0 or not os.path.exists(out_json):
        print(f"ERROR")
        print(result.stderr[-500:])
        volumes.append(None)
        continue

    with open(out_json) as f:
        data = json.load(f)
    vol_L = data["volume_L"]
    volumes.append(vol_L)
    print(f"{vol_L:.3f} L")

waist_df["volume_L"] = volumes
waist_df = waist_df.dropna(subset=["volume_L"])

# ── Sonuçları yazdır ──────────────────────────────────────────────────────────
print()
print("=== Results ===")
print(waist_df[["char_id", "morph_value", "waist_circ_cm", "volume_L"]].to_string(index=False))

corr = waist_df["waist_circ_cm"].corr(waist_df["volume_L"])
print(f"\nPearson r (waist_circ_cm <-> volume_L): {corr:.4f}")

# ── Grafik ────────────────────────────────────────────────────────────────────
fig, axes = plt.subplots(1, 2, figsize=(12, 5))
fig.suptitle("musc_waist series: Waist Circumference vs Mesh Volume", fontsize=13)

ax1 = axes[0]
ax1.plot(waist_df["morph_value"], waist_df["waist_circ_cm"], "o-", color="steelblue")
ax1.set_xlabel("Morph Value")
ax1.set_ylabel("Waist Circumference (cm)")
ax1.set_title("Morph -> Waist Circumference")
ax1.grid(True, alpha=0.3)

ax2 = axes[1]
ax2.scatter(waist_df["waist_circ_cm"], waist_df["volume_L"], color="tomato", zorder=5)
for _, r in waist_df.iterrows():
    ax2.annotate(f"{r.morph_value:.1f}", (r.waist_circ_cm, r.volume_L),
                 textcoords="offset points", xytext=(4, 4), fontsize=8)
ax2.set_xlabel("Waist Circumference (cm)")
ax2.set_ylabel("Mesh Volume (L)")
ax2.set_title(f"Waist Circumference <-> Volume  (r={corr:.3f})")
ax2.grid(True, alpha=0.3)

plt.tight_layout()
out_png = os.path.join(OUT_DIR, "volume_vs_waist.png")
plt.savefig(out_png, dpi=150)
print(f"\nPlot saved: {out_png}")

out_csv = os.path.join(OUT_DIR, "volume_vs_waist.csv")
waist_df[["char_id", "morph_value", "waist_circ_cm", "volume_L"]].to_csv(out_csv, index=False)
print(f"CSV saved:  {out_csv}")
