"""
batch_normal.py — Raw renderlardan StableNormal-turbo ile normal map uretir.

Kullanim:
  python batch_normal.py                    # renders/raw/ altindaki tumu
  python batch_normal.py --id char_00037    # tek karakter
  python batch_normal.py --overwrite        # mevcut normal'lari yeniden uret
  python batch_normal.py --device cpu       # GPU yoksa
  python batch_normal.py --resolution 768   # isleme cozunurlugu (default 1024)

Cikti:
  renders/normal_maps/<char_id>/  -- 8 PNG, RGB'de kodlanmis normal
                                     (R=X, G=Y, B=Z; 128->0.0, 0->-1.0, 255->+1.0)
"""

import sys
import argparse
from pathlib import Path

import numpy as np
import torch
from PIL import Image

# diffusers>=0.30 moved ControlNet modules; patch old import path for StableNormal
try:
    import diffusers.models.controlnet  # noqa: F401
except ImportError:
    import diffusers.models.controlnets.controlnet as _cn
    sys.modules["diffusers.models.controlnet"] = _cn

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
RAW_ROOT    = BASE_DIR / "renders" / "raw"
NORMAL_ROOT = BASE_DIR / "renders" / "normal_maps"

STABLENORMAL_REPO = BASE_DIR.parent / "StableNormal"
if STABLENORMAL_REPO.exists() and str(STABLENORMAL_REPO) not in sys.path:
    sys.path.insert(0, str(STABLENORMAL_REPO))

VIEWS = [
    "front", "front_right", "right", "back_right",
    "back",  "back_left",   "left",  "front_left",
]

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--id",         default=None,  help="Tek char_id (char_00037)")
parser.add_argument("--overwrite",  action="store_true")
parser.add_argument("--device",     default="cuda" if torch.cuda.is_available() else "cpu")
parser.add_argument("--resolution", type=int, default=1024)
parser.add_argument("--yoso-version", default="yoso-normal-v0-3")
args = parser.parse_args()

print(f"Device      : {args.device}")
print(f"Resolution  : {args.resolution}")
print(f"YOSO version: {args.yoso_version}\n")

# ── Model ─────────────────────────────────────────────────────────────────────
print("Loading StableNormal_turbo...")
from stablenormal.pipeline_yoso_normal import YOSONormalsPipeline
from hubconf import Predictor

pipe = YOSONormalsPipeline.from_pretrained(
    f"Stable-X/{args.yoso_version}",
    trust_remote_code=True,
    variant="fp16",
    torch_dtype=torch.float16,
    t_start=0,
    safety_checker=None,
).to(args.device)
predictor = Predictor(pipe, yoso_version=args.yoso_version)
print("Model ready.\n")

# ── Helpers ───────────────────────────────────────────────────────────────────
def extract_mask(src_img: Image.Image) -> np.ndarray | None:
    """Return bool mask (True=subject) or None if no clear background found."""
    if src_img.mode == "RGBA":
        return np.array(src_img.split()[3]) > 10
    # Gray background fallback: detect near-neutral pixels
    rgb = np.array(src_img.convert("RGB")).astype(np.int16)
    diff = rgb.max(axis=2) - rgb.min(axis=2)          # low saturation = background
    brightness = rgb.mean(axis=2)
    return ~((diff < 15) & (brightness > 100) & (brightness < 220))

def apply_mask(normal_map: Image.Image, mask: np.ndarray | None) -> Image.Image:
    """Set background pixels to black in the normal map."""
    if mask is None:
        return normal_map
    arr = np.array(normal_map)
    arr[~mask] = 0
    return Image.fromarray(arr)

# ── Char listesi ──────────────────────────────────────────────────────────────
if args.id:
    char_dirs = [RAW_ROOT / args.id]
else:
    char_dirs = sorted(d for d in RAW_ROOT.iterdir() if d.is_dir())

total = len(char_dirs)
done = skip = fail = 0

print(f"Total: {total} characters")
print(f"  normals -> {NORMAL_ROOT}\n")

for i, char_dir in enumerate(char_dirs):
    char_id = char_dir.name
    out_dir = NORMAL_ROOT / char_id
    prefix  = f"[{i+1}/{total}] {char_id}"

    if not args.overwrite and (out_dir / f"{char_id}_front.png").exists():
        skip += 1
        print(f"{prefix} | SKIP")
        continue

    out_dir.mkdir(parents=True, exist_ok=True)

    try:
        for view in VIEWS:
            src = char_dir / f"{char_id}_{view}.png"
            if not src.exists():
                continue

            raw = Image.open(src)
            mask = extract_mask(raw)
            img = raw.convert("RGB")
            normal_map = predictor(
                img,
                resolution=args.resolution,
                match_input_resolution=True,
                data_type="indoor",
            )
            normal_map = apply_mask(normal_map, mask)
            normal_map.save(out_dir / f"{char_id}_{view}.png")

        done += 1
        print(f"{prefix} | OK")

    except Exception as e:
        fail += 1
        print(f"{prefix} | ERR: {e}")

print(f"\n-- Normals: {done} OK, {skip} skipped, {fail} errors")
