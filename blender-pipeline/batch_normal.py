"""
batch_normal.py — Raw renderlardan DSINE ile normal map uretir.

Kullanim:
  python batch_normal.py                    # renders/raw/ altindaki tumu
  python batch_normal.py --id char_00037    # tek karakter
  python batch_normal.py --overwrite        # mevcut normal'lari yeniden uret
  python batch_normal.py --device cpu       # GPU yoksa

Cikti:
  renders/normal_maps/<char_id>/  -- 8 PNG, RGB'de kodlanmis normal
                                     (R=X, G=Y, B=Z; 128->0.0, 0->-1.0, 255->+1.0)
"""

import sys
import types
import argparse
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

# ── Args ──────────────────────────────────────────────────────────────────────
parser = argparse.ArgumentParser()
parser.add_argument("--id",        default=None, help="Tek char_id (char_00037)")
parser.add_argument("--overwrite", action="store_true")
parser.add_argument("--device",    default="cuda" if torch.cuda.is_available() else "cpu")
args = parser.parse_args()

device = torch.device(args.device)
print(f"Device: {device}\n")

# ── Model ─────────────────────────────────────────────────────────────────────
print("DSINE loading...")

_HUB_DIR = Path(torch.hub.get_dir()) / "baegwangbin_DSINE_main"
if not _HUB_DIR.exists():
    torch.hub.load("baegwangbin/DSINE", "DSINE", trust_repo=True, force_reload=False)

sys.path.insert(0, str(_HUB_DIR))
from models.dsine.v02 import DSINE_v02

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
    print("  Downloading weights...")
    state_dict = torch.hub.load_state_dict_from_url(
        "https://huggingface.co/camenduru/DSINE/resolve/main/dsine.pt",
        file_name="dsine.pt", map_location="cpu"
    )["model"]
else:
    state_dict = torch.load(_CKPT, map_location="cpu")["model"]

model.load_state_dict(state_dict, strict=True)
model = model.to(device).eval()
model.pixel_coords = model.pixel_coords.to(device)
print("Model ready.\n")

# ── Helpers ───────────────────────────────────────────────────────────────────
_normalize = transforms.Normalize(
    mean=[0.485, 0.456, 0.406],
    std =[0.229, 0.224, 0.225],
)

def extract_mask(src_img: Image.Image) -> np.ndarray | None:
    if src_img.mode == "RGBA":
        return np.array(src_img.split()[3]) > 10
    rgb = np.array(src_img.convert("RGB")).astype(np.int16)
    diff = rgb.max(axis=2) - rgb.min(axis=2)
    brightness = rgb.mean(axis=2)
    return ~((diff < 15) & (brightness > 100) & (brightness < 220))

def apply_mask(normal_arr: np.ndarray, mask: np.ndarray | None) -> np.ndarray:
    if mask is not None:
        normal_arr[~mask] = 0
    return normal_arr

def run_dsine(img: Image.Image) -> np.ndarray:
    rgb = img.convert("RGB")
    x = _normalize(transforms.ToTensor()(rgb)).unsqueeze(0).to(device)
    _, _, h, w = x.shape

    pad_h = (32 - h % 32) % 32
    pad_w = (32 - w % 32) % 32
    x_pad = F.pad(x, (0, pad_w, 0, pad_h), mode="constant", value=0.0)

    fx = fy = 1000.0
    K = torch.tensor([[[fx, 0., w/2], [0., fy, h/2], [0., 0., 1.]]],
                     dtype=torch.float32).to(device)

    with torch.no_grad():
        preds = model(x_pad, K, mode="test")
        pred = preds[-1] if isinstance(preds, (list, tuple)) else preds
        pred = pred[:, :, :h, :w]

    n = pred.squeeze(0).permute(1, 2, 0).cpu().numpy()
    return ((n + 1.0) / 2.0 * 255.0).clip(0, 255).astype(np.uint8)

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
            normal_arr = run_dsine(raw)
            normal_arr = apply_mask(normal_arr, mask)
            Image.fromarray(normal_arr).save(out_dir / f"{char_id}_{view}.png")

        done += 1
        print(f"{prefix} | OK")

    except Exception as e:
        fail += 1
        print(f"{prefix} | ERR: {e}")

print(f"\n-- Normals: {done} OK, {skip} skipped, {fail} errors")
