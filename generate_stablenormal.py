"""
generate_stablenormal.py — external_images/ altındaki görseller için
StableNormal_turbo ile normal map üretir.

Kullanım:
  python generate_stablenormal.py
  python generate_stablenormal.py --device cpu
  python generate_stablenormal.py --resolution 768
  python generate_stablenormal.py --data-type object   # arka plan maskeli
"""

import sys
import argparse
from pathlib import Path

import torch
from PIL import Image

# diffusers>=0.30 moved ControlNet modules; patch old import path for StableNormal compatibility
try:
    import diffusers.models.controlnet  # noqa: F401
except ImportError:
    import diffusers.models.controlnets.controlnet as _cn
    sys.modules["diffusers.models.controlnet"] = _cn

SCRIPT_DIR = Path(__file__).resolve().parent
IMG_DIR    = SCRIPT_DIR / "external_images"
OUT_DIR    = IMG_DIR / "normals_stablenormal"
EXTS       = {".jpg", ".jpeg", ".png", ".webp"}

# StableNormal repo'su workspace altında klonlanmış olmalı
STABLENORMAL_REPO = Path(__file__).resolve().parent.parent / "StableNormal"
if STABLENORMAL_REPO.exists() and str(STABLENORMAL_REPO) not in sys.path:
    sys.path.insert(0, str(STABLENORMAL_REPO))

parser = argparse.ArgumentParser()
parser.add_argument("--device",     default="cuda" if torch.cuda.is_available() else "cpu")
parser.add_argument("--resolution", type=int, default=1024)
parser.add_argument("--data-type",  default="indoor",
                    choices=["indoor", "object", "outdoor"],
                    help="indoor: maske yok | object: BiRefNet arka plan | outdoor: gökyüzü/bitki maskesi")
parser.add_argument("--yoso-version", default="yoso-normal-v0-3",
                    help="HuggingFace model versiyonu (default: yoso-normal-v0-3)")
args = parser.parse_args()

device = args.device
print(f"Device      : {device}")
print(f"Resolution  : {args.resolution}")
print(f"Data type   : {args.data_type}")
print(f"YOSO version: {args.yoso_version}\n")

# ── Model yükle ───────────────────────────────────────────────────────────────
print("Loading StableNormal_turbo (model will be downloaded on first run)...")

from stablenormal.pipeline_yoso_normal import YOSONormalsPipeline
from hubconf import Predictor

hf_repo = f"Stable-X/{args.yoso_version}"
pipe = YOSONormalsPipeline.from_pretrained(
    hf_repo,
    trust_remote_code=True,
    variant="fp16",
    torch_dtype=torch.float16,
    t_start=0,
    safety_checker=None,
).to(device)
predictor = Predictor(pipe, yoso_version=args.yoso_version)
print("Model ready.\n")

# ── Görselleri işle ───────────────────────────────────────────────────────────
images = sorted(p for p in IMG_DIR.iterdir() if p.suffix.lower() in EXTS)
if not images:
    print(f"No images found in: {IMG_DIR}")
    sys.exit(1)

OUT_DIR.mkdir(exist_ok=True)
print(f"{len(images)} images found -> {OUT_DIR}\n")

for img_path in images:
    out_path = OUT_DIR / (img_path.stem + "_normal.png")
    try:
        img = Image.open(img_path).convert("RGB")
        normal_map = predictor(
            img,
            resolution=args.resolution,
            match_input_resolution=True,
            data_type=args.data_type,
        )
        normal_map.save(out_path)
        print(f"  OK   {img_path.name}  ->  {out_path.name}")
    except Exception as e:
        print(f"  ERR  {img_path.name}: {e}")

print("\nDone.")
