"""
Training script.

Colab usage:
    from ml.config import TrainConfig
    from ml.train import train
    cfg = TrainConfig()
    cfg.data_root = "/content/drive/MyDrive/renders"
    train(cfg)
"""

import os
import json
import math
import time
import random
import numpy as np

import torch
import torch.nn as nn
import torch.nn.functional as F
from torch.utils.data import DataLoader
from torch.cuda.amp import GradScaler, autocast

from .config import TrainConfig, MEASUREMENTS
from .dataset import build_datasets
from .model import build_model


# ─── Loss ────────────────────────────────────────────────────────────────────

def measurement_loss(preds, targets):
    return F.huber_loss(preds, targets, delta=1.0)

def seg_loss(seg_logits, gt_seg_cls):
    """
    seg_logits : [B, V, K, Hs, Ws]
    gt_seg_cls : [B, V, H, W]  int64
    """
    B, V, K, Hs, Ws = seg_logits.shape
    logits_flat = seg_logits.view(B * V, K, Hs, Ws)

    # Resize GT to match seg head output resolution
    gt_flat = gt_seg_cls.view(B * V, 1, *gt_seg_cls.shape[-2:]).float()
    gt_small = F.interpolate(gt_flat, size=(Hs, Ws), mode="nearest").long().squeeze(1)

    return F.cross_entropy(logits_flat, gt_small)


# ─── LR schedule ─────────────────────────────────────────────────────────────

def cosine_with_warmup(optimizer, step, total_steps, warmup_steps):
    if step < warmup_steps:
        scale = (step + 1) / warmup_steps
    else:
        progress = (step - warmup_steps) / max(1, total_steps - warmup_steps)
        scale = 0.5 * (1.0 + math.cos(math.pi * progress))
    for pg in optimizer.param_groups:
        pg["lr"] = pg["base_lr"] * scale


# ─── Metrics ─────────────────────────────────────────────────────────────────

def compute_mae(preds_norm, targets_norm, std: dict) -> dict:
    """MAE in original units (cm / L)."""
    std_arr = np.array([std[m] for m in MEASUREMENTS])
    mae_per = np.abs((preds_norm - targets_norm) * std_arr).mean(axis=0)
    metrics = {m: float(mae_per[i]) for i, m in enumerate(MEASUREMENTS)}
    metrics["mean_mae"] = float(mae_per.mean())
    return metrics


# ─── Train loop ──────────────────────────────────────────────────────────────

def train(cfg: TrainConfig):
    random.seed(cfg.seed)
    np.random.seed(cfg.seed)
    torch.manual_seed(cfg.seed)

    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    print(f"Device: {device}")

    os.makedirs(cfg.checkpoint_dir, exist_ok=True)

    # Data
    train_ds, val_ds, color_map = build_datasets(
        cfg.data_root, cfg.img_size, cfg.val_split, cfg.seed
    )

    # Persist normalisation stats + color map for inference
    with open(os.path.join(cfg.checkpoint_dir, "norm_stats.json"), "w") as f:
        json.dump({"mean": train_ds.mean, "std": train_ds.std}, f, indent=2)
    with open(os.path.join(cfg.checkpoint_dir, "color_map.json"), "w") as f:
        # keys must be strings for JSON
        json.dump({str(k): v for k, v in color_map.items()}, f, indent=2)

    # Update cfg seg classes from actual data
    cfg.num_seg_classes = len(color_map)
    print(f"Seg classes: {cfg.num_seg_classes}")
    print(f"Train: {len(train_ds)}  Val: {len(val_ds)}")

    train_loader = DataLoader(
        train_ds, batch_size=cfg.batch_size, shuffle=True,
        num_workers=cfg.num_workers, pin_memory=True, drop_last=True,
    )
    val_loader = DataLoader(
        val_ds, batch_size=cfg.batch_size, shuffle=False,
        num_workers=cfg.num_workers, pin_memory=True,
    )

    # Model
    model = build_model(cfg).to(device)

    # Separate LR for backbone (lower) vs rest
    backbone_ids = {id(p) for p in model.backbone.parameters()}
    optimizer = torch.optim.AdamW(
        [
            {"params": [p for p in model.parameters() if id(p) in backbone_ids],
             "base_lr": cfg.lr_backbone, "lr": cfg.lr_backbone},
            {"params": [p for p in model.parameters() if id(p) not in backbone_ids],
             "base_lr": cfg.lr, "lr": cfg.lr},
        ],
        weight_decay=cfg.weight_decay,
    )

    scaler      = GradScaler()
    total_steps = cfg.epochs * len(train_loader)
    warmup_steps = cfg.warmup_epochs * len(train_loader)

    best_val_mae = float("inf")
    history = []

    for epoch in range(cfg.epochs):
        # ── Train ──────────────────────────────────────────────────────────
        model.train()
        t0 = time.time()
        train_meas_loss = train_seg_loss = 0.0

        for step, batch in enumerate(train_loader):
            global_step = epoch * len(train_loader) + step
            cosine_with_warmup(optimizer, global_step, total_steps, warmup_steps)

            normal_sils  = batch["normal_sils"].to(device)
            gt_seg_cls   = batch["gt_seg_cls"].to(device)
            targets      = batch["targets"].to(device)

            # height_weight: user-provided inputs, not targets
            # batch must include "height_cm" and "weight_kg" from dataset
            height_weight = batch["height_weight"].to(device)  # [B, 2]

            optimizer.zero_grad(set_to_none=True)
            with autocast():
                # Training: pass gt_seg_cls → GT masks used for masked pooling
                preds, seg_logits = model(normal_sils, height_weight, gt_seg_cls)

                l_meas = measurement_loss(preds, targets)
                l_seg  = seg_loss(seg_logits, gt_seg_cls)
                loss   = l_meas + cfg.seg_loss_weight * l_seg

            scaler.scale(loss).backward()
            scaler.unscale_(optimizer)
            nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
            scaler.step(optimizer)
            scaler.update()

            train_meas_loss += l_meas.item()
            train_seg_loss  += l_seg.item()

        train_meas_loss /= len(train_loader)
        train_seg_loss  /= len(train_loader)

        # ── Validate ───────────────────────────────────────────────────────
        model.eval()
        all_preds, all_targets = [], []
        val_meas_loss = val_seg_loss = 0.0

        with torch.no_grad():
            for batch in val_loader:
                normal_sils  = batch["normal_sils"].to(device)
                gt_seg_cls   = batch["gt_seg_cls"].to(device)
                targets      = batch["targets"].to(device)

                height_weight = torch.stack([
                    targets[:, 0],
                    targets[:, MEASUREMENTS.index("volume_L")],
                ], dim=1)

                with autocast():
                    # Validation: no gt_seg_cls → predicted masks (mirrors inference)
                    preds, seg_logits = model(normal_sils, height_weight)
                    val_meas_loss += measurement_loss(preds, targets).item()
                    val_seg_loss  += seg_loss(seg_logits, gt_seg_cls).item()

                all_preds.append(preds.cpu().numpy())
                all_targets.append(targets.cpu().numpy())

        val_meas_loss /= len(val_loader)
        val_seg_loss  /= len(val_loader)

        metrics = compute_mae(
            np.concatenate(all_preds),
            np.concatenate(all_targets),
            train_ds.std,
        )

        elapsed = time.time() - t0
        print(
            f"Epoch {epoch+1:3d}/{cfg.epochs} | "
            f"meas={train_meas_loss:.4f}/{val_meas_loss:.4f}  "
            f"seg={train_seg_loss:.4f}/{val_seg_loss:.4f} | "
            f"MAE={metrics['mean_mae']:.2f} cm | "
            f"{elapsed:.0f}s"
        )

        history.append({
            "epoch": epoch + 1,
            "train_meas_loss": train_meas_loss,
            "train_seg_loss":  train_seg_loss,
            "val_meas_loss":   val_meas_loss,
            "val_seg_loss":    val_seg_loss,
            **metrics,
        })

        if metrics["mean_mae"] < best_val_mae:
            best_val_mae = metrics["mean_mae"]
            torch.save({
                "epoch": epoch + 1,
                "model_state": model.state_dict(),
                "best_val_mae": best_val_mae,
                "metrics": metrics,
                "num_seg_classes": cfg.num_seg_classes,
            }, os.path.join(cfg.checkpoint_dir, "best.pt"))
            print(f"  Saved best (MAE={best_val_mae:.2f} cm)")

        with open(os.path.join(cfg.checkpoint_dir, "history.json"), "w") as f:
            json.dump(history, f, indent=2)

    print(f"\nDone. Best val MAE: {best_val_mae:.2f} cm")
    return history


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--data_root", required=True)
    parser.add_argument("--checkpoint_dir", default="checkpoints")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--batch_size", type=int, default=8)
    args = parser.parse_args()

    cfg = TrainConfig()
    cfg.data_root      = args.data_root
    cfg.checkpoint_dir = args.checkpoint_dir
    cfg.epochs         = args.epochs
    cfg.batch_size     = args.batch_size
    train(cfg)
