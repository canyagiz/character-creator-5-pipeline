"""
Body Measurement Regressor — MaskAttentive Multi-View architecture.

Training:
    predictions, seg_logits = model(normal_sils, height_weight, gt_seg_cls)
    - gt_seg_cls : [B, V, H, W] integer class map  → GT masks used for pooling
    - seg_logits : [B, V, K, Hs, Ws]               → used for L_seg only

Inference:
    predictions, seg_logits = model(normal_sils, height_weight)
    - gt_seg_cls omitted → predicted masks used for pooling
"""

import torch
import torch.nn as nn
import torch.nn.functional as F
import timm

from .config import MEASUREMENTS, VIEWS

NUM_MEASUREMENTS = len(MEASUREMENTS)
NUM_VIEWS        = len(VIEWS)


# ─── Backbone ────────────────────────────────────────────────────────────────

class Backbone(nn.Module):
    """
    EfficientNet-B3, 4-channel input, features_only.

    Returns:
        feat_64 : [B, 32,  128, 128]  stride-4  (skip for seg head)
        feat_32 : [B, 48,   64,  64]  stride-8  (skip for seg head)
        F_map   : [B, 384,  16,  16]  stride-32 (main features)
    """
    CH_FEAT64 = 32
    CH_FEAT32 = 48
    CH_F      = 384

    def __init__(self, backbone_name: str = "efficientnet_b3"):
        super().__init__()
        self.net = timm.create_model(
            backbone_name,
            pretrained=True,
            features_only=True,
            out_indices=(1, 2, 4),
            in_chans=4,
        )

    def forward(self, x: torch.Tensor):
        feat_64, feat_32, F_map = self.net(x)
        return feat_64, feat_32, F_map


# ─── Seg Head ────────────────────────────────────────────────────────────────

class SegHead(nn.Module):
    """
    U-Net decoder: F_map (8×8) → seg logits (64×64).

    Skip connections from feat_32 and feat_64 recover spatial detail.
    Output is raw logits (no softmax) — conversion happens in MaskedPooling.
    """

    def __init__(self, num_classes: int):
        super().__init__()

        self.reduce_f = nn.Sequential(
            nn.Conv2d(Backbone.CH_F, 256, 1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
        )

        # 8→16 (no skip)
        self.up1 = nn.Sequential(
            nn.Conv2d(256, 256, 3, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
        )

        # 16→32 + skip feat_32
        self.skip_32 = nn.Sequential(
            nn.Conv2d(Backbone.CH_FEAT32, 128, 1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )
        self.up2 = nn.Sequential(
            nn.Conv2d(256 + 128, 256, 3, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.ReLU(inplace=True),
        )

        # 32→64 + skip feat_64
        self.skip_64 = nn.Sequential(
            nn.Conv2d(Backbone.CH_FEAT64, 64, 1, bias=False),
            nn.BatchNorm2d(64),
            nn.ReLU(inplace=True),
        )
        self.up3 = nn.Sequential(
            nn.Conv2d(256 + 64, 128, 3, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.ReLU(inplace=True),
        )

        self.out_conv = nn.Conv2d(128, num_classes, 1)

    def forward(self, F_map, feat_32, feat_64):
        x = self.reduce_f(F_map)

        x = F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
        x = self.up1(x)                                              # [B, 256, 16, 16]

        x = F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
        x = torch.cat([x, self.skip_32(feat_32)], dim=1)
        x = self.up2(x)                                              # [B, 256, 32, 32]

        x = F.interpolate(x, scale_factor=2, mode="bilinear", align_corners=False)
        x = torch.cat([x, self.skip_64(feat_64)], dim=1)
        x = self.up3(x)                                              # [B, 128, 64, 64]

        return self.out_conv(x)                                      # [B, K, 64, 64]


# ─── Masked Pooling ──────────────────────────────────────────────────────────

class MaskedPooling(nn.Module):
    """
    Produces a fixed-size view feature from F_map and spatial attention weights.

    seg_weights : [B, K, H, W]  — already normalised:
        Training  → one-hot from GT class map (hard, clean attention)
        Inference → softmax(seg_logits)      (soft, predicted attention)

    For each class k:
        region_feat_k = weighted_avg_pool(F_map, seg_weights[:, k])

    All K region features + 1 global feature projected to region_dim each.
    Output dim: (K+1) * region_dim
    """

    def __init__(self, num_classes: int, region_dim: int):
        super().__init__()
        self.num_classes = num_classes
        self.region_proj = nn.Sequential(
            nn.Linear(Backbone.CH_F, region_dim),
            nn.ReLU(inplace=True),
        )
        self.out_dim = (num_classes + 1) * region_dim

    def forward(self, F_map: torch.Tensor, seg_weights: torch.Tensor) -> torch.Tensor:
        # F_map      : [B, C, Hf, Wf]
        # seg_weights: [B, K, Hs, Ws]  (already normalised)
        B, C, Hf, Wf = F_map.shape

        w = F.interpolate(seg_weights, size=(Hf, Wf), mode="bilinear", align_corners=False)

        # Weighted average pool per class: [B, K, C]
        F_exp = F_map.unsqueeze(1)   # [B, 1, C, Hf, Wf]
        w_exp = w.unsqueeze(2)       # [B, K, 1, Hf, Wf]
        region_feats = (F_exp * w_exp).mean(dim=(-2, -1))  # [B, K, C]

        # Global (unmasked) feature: [B, 1, C]
        global_feat = F_map.mean(dim=(-2, -1)).unsqueeze(1)

        all_feats = torch.cat([region_feats, global_feat], dim=1)   # [B, K+1, C]
        projected = self.region_proj(all_feats)                      # [B, K+1, region_dim]
        return projected.view(B, -1)                                 # [B, (K+1)*region_dim]


# ─── View Aggregator ─────────────────────────────────────────────────────────

class ViewAggregator(nn.Module):
    """Projects V view features to embed_dim, then learned-attention weighted sum."""

    def __init__(self, view_dim: int, embed_dim: int):
        super().__init__()
        self.proj = nn.Sequential(
            nn.Linear(view_dim, embed_dim),
            nn.LayerNorm(embed_dim),
            nn.GELU(),
        )
        self.attn_score = nn.Linear(embed_dim, 1)

    def forward(self, view_feats: torch.Tensor) -> torch.Tensor:
        # view_feats: [B, V, view_dim]
        embeds  = self.proj(view_feats)           # [B, V, embed_dim]
        weights = torch.softmax(self.attn_score(embeds), dim=1)  # [B, V, 1]
        return (embeds * weights).sum(dim=1)      # [B, embed_dim]


# ─── FiLM ────────────────────────────────────────────────────────────────────

class FiLM(nn.Module):
    """
    Height + weight condition the global embedding.
    output = embed * (1 + gamma) + beta
    Zero-init on last layer → identity at init.
    """

    def __init__(self, embed_dim: int):
        super().__init__()
        self.mlp = nn.Sequential(
            nn.Linear(2, 64),
            nn.ReLU(inplace=True),
            nn.Linear(64, 128),
            nn.ReLU(inplace=True),
            nn.Linear(128, embed_dim * 2),
        )
        nn.init.zeros_(self.mlp[-1].weight)
        nn.init.zeros_(self.mlp[-1].bias)

    def forward(self, embed: torch.Tensor, height_weight: torch.Tensor) -> torch.Tensor:
        gamma, beta = self.mlp(height_weight).chunk(2, dim=-1)
        return embed * (1.0 + gamma) + beta


# ─── Regression Head ─────────────────────────────────────────────────────────

class RegressionHead(nn.Module):
    def __init__(self, embed_dim: int, num_measurements: int, dropout: float):
        super().__init__()
        self.net = nn.Sequential(
            nn.Linear(embed_dim, 256), nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(256, 128), nn.GELU(),
            nn.Linear(128, num_measurements),
        )

    def forward(self, x):
        return self.net(x)


# ─── Full Model ──────────────────────────────────────────────────────────────

class BodyMeasurementModel(nn.Module):
    def __init__(
        self,
        backbone: str = "efficientnet_b3",
        num_seg_classes: int = 15,
        region_dim: int = 128,
        embed_dim: int = 512,
        dropout: float = 0.3,
        num_measurements: int = NUM_MEASUREMENTS,
        num_views: int = NUM_VIEWS,
    ):
        super().__init__()
        self.num_views       = num_views
        self.num_seg_classes = num_seg_classes

        self.backbone    = Backbone(backbone)
        self.seg_head    = SegHead(num_seg_classes)
        self.masked_pool = MaskedPooling(num_seg_classes, region_dim)
        self.view_agg    = ViewAggregator(self.masked_pool.out_dim, embed_dim)
        self.film        = FiLM(embed_dim)
        self.head        = RegressionHead(embed_dim, num_measurements, dropout)

    def forward(
        self,
        normal_sils: torch.Tensor,          # [B, V, 4, H, W]
        height_weight: torch.Tensor,        # [B, 2]
        gt_seg_cls: torch.Tensor = None,    # [B, V, H, W]  int — training only
    ):
        B, V, C, H, W = normal_sils.shape

        # Merge batch + view for parallel processing
        x = normal_sils.view(B * V, C, H, W)
        feat_64, feat_32, F_map = self.backbone(x)
        seg_logits = self.seg_head(F_map, feat_32, feat_64)   # [B*V, K, 64, 64]

        # --- Choose seg weights for masked pooling ---
        if gt_seg_cls is not None:
            # Training: one-hot from GT → hard, clean attention
            # gt_seg_cls: [B, V, H, W] → [B*V, H, W]
            cls_flat = gt_seg_cls.view(B * V, H, W)
            # Resize to seg head output resolution (64×64)
            cls_small = F.interpolate(
                cls_flat.unsqueeze(1).float(),
                size=seg_logits.shape[-2:],
                mode="nearest",
            ).long().squeeze(1)                               # [B*V, 64, 64]
            seg_weights = F.one_hot(cls_small, self.num_seg_classes) \
                           .permute(0, 3, 1, 2).float()      # [B*V, K, 64, 64]
        else:
            # Inference: softmax over predicted logits → soft attention
            seg_weights = F.softmax(seg_logits, dim=1)       # [B*V, K, 64, 64]

        # Masked pooling → view features
        view_feats = self.masked_pool(F_map, seg_weights)    # [B*V, (K+1)*region_dim]
        view_feats = view_feats.view(B, V, -1)               # [B, V, view_dim]

        seg_logits = seg_logits.view(B, V, *seg_logits.shape[1:])  # [B, V, K, 64, 64]

        global_embed = self.view_agg(view_feats)             # [B, embed_dim]
        conditioned  = self.film(global_embed, height_weight) # [B, embed_dim]
        predictions  = self.head(conditioned)                 # [B, num_measurements]

        return predictions, seg_logits


def build_model(cfg) -> BodyMeasurementModel:
    return BodyMeasurementModel(
        backbone=cfg.backbone,
        num_seg_classes=cfg.num_seg_classes,
        region_dim=cfg.region_dim,
        embed_dim=cfg.embed_dim,
        dropout=cfg.dropout,
    )
