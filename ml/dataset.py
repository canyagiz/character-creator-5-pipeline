import os
import json
import random
import numpy as np
import torch
import torch.nn.functional as F
from torch.utils.data import Dataset
from torchvision import transforms
from PIL import Image

from .config import MEASUREMENTS, VIEWS, FLIP_VIEW_PAIRS


# ─── Color map ───────────────────────────────────────────────────────────────

def build_color_map(root_dir: str, char_ids: list, num_samples: int = 30) -> dict:
    """
    Scans seg masks from a subset of samples to find all unique RGB colors.
    Returns {(R,G,B): class_index} sorted so (0,0,0) background = class 0.
    """
    colors = set()
    sample_ids = char_ids[:num_samples]

    for cid in sample_ids:
        for view in VIEWS:
            path = os.path.join(root_dir, "segmentation", cid, f"{cid}_{view}.png")
            img = np.array(Image.open(path).convert("RGB"))
            pixels = img.reshape(-1, 3)
            for c in np.unique(pixels, axis=0):
                colors.add(tuple(int(v) for v in c))

    # Sort: (0,0,0) first (background = class 0), rest alphabetically
    colors = sorted(colors, key=lambda c: (c != (0, 0, 0), c))
    return {color: idx for idx, color in enumerate(colors)}


def _make_lut(color_map: dict) -> np.ndarray:
    """
    Build a [256, 256, 256] uint8 lookup table for fast RGB→class conversion.
    lut[R, G, B] = class_index
    """
    lut = np.zeros((256, 256, 256), dtype=np.uint8)
    for (r, g, b), cls in color_map.items():
        lut[r, g, b] = cls
    return lut


def rgb_to_class_map(img_rgb: np.ndarray, lut: np.ndarray) -> np.ndarray:
    """img_rgb: [H, W, 3] uint8 → class_map: [H, W] int64"""
    return lut[img_rgb[:, :, 0], img_rgb[:, :, 1], img_rgb[:, :, 2]].astype(np.int64)


# ─── Dataset ─────────────────────────────────────────────────────────────────

class BodyMeasurementDataset(Dataset):
    def __init__(
        self,
        root_dir: str,
        char_ids: list,
        color_map: dict,
        img_size: int = 256,
        augment: bool = False,
        mean: dict = None,
        std: dict = None,
    ):
        self.root_dir  = root_dir
        self.char_ids  = char_ids
        self.color_map = color_map
        self.lut       = _make_lut(color_map)
        self.img_size  = img_size
        self.augment   = augment
        self.mean, self.std = (mean, std) if mean else self._compute_stats()

    # ── Stats ──────────────────────────────────────────────────────────────

    def _compute_stats(self):
        all_vals = {m: [] for m in MEASUREMENTS}
        for cid in self.char_ids:
            meta = self._load_meta(cid)
            for m in MEASUREMENTS:
                all_vals[m].append(meta[m])
        mean = {m: float(np.mean(all_vals[m])) for m in MEASUREMENTS}
        std  = {m: float(np.std(all_vals[m])) + 1e-6 for m in MEASUREMENTS}
        return mean, std

    # ── Loaders ────────────────────────────────────────────────────────────

    def _load_meta(self, cid: str) -> dict:
        with open(os.path.join(self.root_dir, "meta", f"{cid}_meta.json")) as f:
            return json.load(f)

    def _load_rgb(self, folder: str, cid: str, view: str) -> torch.Tensor:
        path = os.path.join(self.root_dir, folder, cid, f"{cid}_{view}.png")
        img = Image.open(path).convert("RGB").resize((self.img_size, self.img_size), Image.BILINEAR)
        return transforms.ToTensor()(img)   # [3, H, W]

    def _load_sil(self, cid: str, view: str) -> torch.Tensor:
        path = os.path.join(self.root_dir, "silhouettes", cid, f"{cid}_{view}.png")
        img = Image.open(path).convert("L").resize((self.img_size, self.img_size), Image.BILINEAR)
        return transforms.ToTensor()(img)   # [1, H, W]

    def _load_seg_cls(self, cid: str, view: str) -> torch.Tensor:
        """Returns integer class map [H, W]."""
        path = os.path.join(self.root_dir, "segmentation", cid, f"{cid}_{view}.png")
        img = np.array(
            Image.open(path).convert("RGB").resize(
                (self.img_size, self.img_size), Image.NEAREST   # no color blending
            )
        )
        cls_map = rgb_to_class_map(img, self.lut)
        return torch.from_numpy(cls_map)    # [H, W]  int64

    # ── __getitem__ ────────────────────────────────────────────────────────

    def __len__(self):
        return len(self.char_ids)

    def __getitem__(self, idx):
        cid  = self.char_ids[idx]
        meta = self._load_meta(cid)

        targets = torch.tensor(
            [(meta[m] - self.mean[m]) / self.std[m] for m in MEASUREMENTS],
            dtype=torch.float32,
        )

        # User-provided inputs — normalised with fixed population stats
        height_cm = (meta["height_cm"] - 170.0) / 10.0
        weight_kg = (meta.get("weight_kg", meta["volume_L"] * 0.985) - 75.0) / 15.0
        height_weight = torch.tensor([height_cm, weight_kg], dtype=torch.float32)

        do_flip = self.augment and random.random() > 0.5

        normal_sils, seg_cls_maps = [], []

        for view in VIEWS:
            load_view = FLIP_VIEW_PAIRS[view] if do_flip else view

            nm  = self._load_rgb("normal_maps", cid, load_view)   # [3, H, W]
            sil = self._load_sil(cid, load_view)                  # [1, H, W]
            seg = self._load_seg_cls(cid, load_view)              # [H, W]

            if do_flip:
                nm  = torch.flip(nm,  dims=[-1])
                sil = torch.flip(sil, dims=[-1])
                seg = torch.flip(seg, dims=[-1])

            normal_sils.append(torch.cat([nm, sil], dim=0))       # [4, H, W]
            seg_cls_maps.append(seg)

        return {
            "normal_sils":  torch.stack(normal_sils),   # [V, 4, H, W]
            "gt_seg_cls":   torch.stack(seg_cls_maps),  # [V, H, W]  int64
            "targets":      targets,                    # [25]
            "height_weight": height_weight,             # [2]
            "char_id":      cid,
        }


# ─── Build helper ────────────────────────────────────────────────────────────

def build_datasets(root_dir: str, img_size: int = 256, val_split: float = 0.1, seed: int = 42):
    all_ids = sorted(
        f.replace("_meta.json", "")
        for f in os.listdir(os.path.join(root_dir, "meta"))
        if f.endswith("_meta.json")
    )

    rng = random.Random(seed)
    rng.shuffle(all_ids)
    n_val     = max(1, int(len(all_ids) * val_split))
    val_ids   = all_ids[:n_val]
    train_ids = all_ids[n_val:]

    print(f"Building color map from {min(30, len(train_ids))} samples...")
    color_map = build_color_map(root_dir, train_ids)
    print(f"  Found {len(color_map)} seg classes: {list(color_map.keys())[:5]} ...")

    train_ds = BodyMeasurementDataset(root_dir, train_ids, color_map, img_size, augment=True)
    val_ds   = BodyMeasurementDataset(
        root_dir, val_ids, color_map, img_size, augment=False,
        mean=train_ds.mean, std=train_ds.std,
    )
    return train_ds, val_ds, color_map
