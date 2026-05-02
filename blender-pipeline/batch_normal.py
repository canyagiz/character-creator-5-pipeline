"""
batch_normal.py — Raw renderlardan DSINE ile normal map üretir.

Kullanım:
  python batch_normal.py                    # renders/raw/ altındaki tümü
  python batch_normal.py --id char_00037    # tek karakter
  python batch_normal.py --overwrite        # mevcut normal'ları yeniden üret
  python batch_normal.py --device cpu       # GPU yoksa

Çıktı:
  renders/normals/<char_id>/  — 8 PNG, RGB'de kodlanmış view-space normal
                                 (R=X, G=Y, B=Z; 128 → 0.0, 0 → -1.0, 255 → +1.0)
"""

import os
import sys
import argparse
import types
from pathlib import Path

import numpy as np
import torch
import torch.nn.functional as F
from PIL import Image
from torchvision import transforms

# ── Paths ─────────────────────────────────────────────────────────────────────
BASE_DIR    = Path(__file__).resolve().parent.parent
RAW_ROOT    = BASE_DIR / "renders" / "raw"
NORMAL_ROOT = BASE_DIR / "renders" / "normal_maps"

VIEWS = [
    "front", "front_right", "right", "back_right",
    "back",  "back_left",   "left",  "front_left",
]

# Blender kamera ayarlarıyla eşleşen intrinsics (85mm lens, 36mm sensor, 512px)
_FOCAL_PX = (85.0 / 36.0) * 512  # ≈ 1208
_CX = _CY = 256.0

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--id",        default=None,  help="Tek char_id (char_00037)")
parser.add_argument("--overwrite", action="store_true")
parser.add_argument("--device",    default="cuda" if torch.cuda.is_available() else "cpu")
args = parser.parse_args()

device = torch.device(args.device)
print(f"Device: {device}")

# ── Model ─────────────────────────────────────────────────────────────────────
print("DSINE yükleniyor (ilk çalıştırmada ağırlıklar indirilir)...")

# torch.hub'ın hubconf'u bozuk — modeli doğrudan cached repo'dan yükle
_HUB_DIR = Path(torch.hub.get_dir()) / "baegwangbin_DSINE_main"
if not _HUB_DIR.exists():
    # Henüz indirilmemişse bir kez hub ile sadece repo'yu çek
    torch.hub.load("baegwangbin/DSINE", "DSINE", trust_repo=True, force_reload=False)

sys.path.insert(0, str(_HUB_DIR))
from models.dsine.v02 import DSINE_v02

# DSINE_v02'nin beklediği argümanlar (checkpoint ile eşleşen defaults)
_args = types.SimpleNamespace(
    NNET_encoder_B=5,
    NNET_decoder_NF=2048,
    NNET_decoder_BN=False,
    NNET_decoder_down=8,
    NNET_output_dim=3,
    NNET_feature_dim=64,
    NNET_hidden_dim=64,
    NNET_learned_upsampling=True,
    NRN_prop_ps=5,
    NRN_num_iter_train=5,
    NRN_num_iter_test=5,
    NRN_ray_relu=True,
)

model = DSINE_v02(_args)

_CKPT = Path(torch.hub.get_dir()) / "checkpoints" / "dsine.pt"
if not _CKPT.exists():
    print("  Ağırlıklar indiriliyor...")
    state_dict = torch.hub.load_state_dict_from_url(
        "https://huggingface.co/camenduru/DSINE/resolve/main/dsine.pt",
        file_name="dsine.pt", map_location="cpu"
    )["model"]
else:
    state_dict = torch.load(_CKPT, map_location="cpu")["model"]

model.load_state_dict(state_dict, strict=True)
model = model.to(device).eval()
model.pixel_coords = model.pixel_coords.to(device)
print("Model hazır.\n")

# ── Helpers ───────────────────────────────────────────────────────────────────
_normalize = transforms.Normalize(
    mean=[0.485, 0.456, 0.406],
    std =[0.229, 0.224, 0.225],
)

def load_tensor(path: Path) -> torch.Tensor:
    img = Image.open(path).convert("RGB")
    x = transforms.ToTensor()(img)        # [3, H, W], float32 [0,1]
    return _normalize(x).unsqueeze(0)     # [1, 3, H, W]

def intrinsics_tensor(h: int, w: int) -> torch.Tensor:
    # DSINE_v02 forward() beklediği format: [B, 3, 3] — 3x3 K matrisi
    fx = _FOCAL_PX * (w / 512)
    fy = _FOCAL_PX * (h / 512)
    cx = w / 2.0
    cy = h / 2.0
    K = torch.tensor([[
        [fx,  0., cx],
        [0.,  fy, cy],
        [0.,  0.,  1.],
    ]], dtype=torch.float32)  # [1, 3, 3]
    return K

def save_normal(pred: torch.Tensor, path: Path) -> None:
    # pred beklenen şekil: [1, 3, H, W] veya [1, H, W, 3]
    n = pred.squeeze(0)
    if n.shape[0] == 3:          # [3, H, W] → [H, W, 3]
        n = n.permute(1, 2, 0)
    n = n.cpu().numpy()          # float32, değerler [-1, 1]
    rgb = ((n + 1.0) / 2.0 * 255.0).clip(0, 255).astype(np.uint8)
    Image.fromarray(rgb).save(path)

# ── Char listesi ──────────────────────────────────────────────────────────────
if args.id:
    char_dirs = [RAW_ROOT / args.id]
else:
    char_dirs = sorted(d for d in RAW_ROOT.iterdir() if d.is_dir())

total = len(char_dirs)
done = skip = fail = 0

print(f"Toplam: {total} karakter")
print(f"  normal  : {NORMAL_ROOT}\n")

for i, char_dir in enumerate(char_dirs):
    char_id  = char_dir.name
    out_dir  = NORMAL_ROOT / char_id
    prefix   = f"[{i+1}/{total}] {char_id}"

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

            x      = load_tensor(src).to(device)           # [1, 3, H, W]
            _, _, h, w = x.shape

            # Padding: H ve W 32'nin katı olmalı (DSINE gereksinimi)
            pad_h = (32 - h % 32) % 32
            pad_w = (32 - w % 32) % 32
            x_pad = F.pad(x, (0, pad_w, 0, pad_h), mode="constant", value=0.0)

            intrin = intrinsics_tensor(h, w).to(device)    # [1, 3, 3]

            with torch.no_grad():
                preds = model(x_pad, intrin, mode='test')
                # DSINE çoklu ölçek döner; son eleman en ince
                pred = preds[-1] if isinstance(preds, (list, tuple)) else preds
                pred = pred[:, :, :h, :w]                  # padding'i kırp

            save_normal(pred, out_dir / f"{char_id}_{view}.png")

        done += 1
        print(f"{prefix} | OK")

    except Exception as e:
        fail += 1
        print(f"{prefix} | HATA: {e}")

# ── Özet ──────────────────────────────────────────────────────────────────────
print(f"\n-- Normal: {done} OK, {skip} atlandi, {fail} hata")
