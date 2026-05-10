"""
ONNX export for Netron visualisation.

Two exports:
  model_singleview.onnx  — one view, shows the full pipeline clearly
  model.onnx             — full 8-view model

Usage:
    python -m ml.export_onnx
"""

import argparse
import torch
import torch.nn as nn
from .model import Backbone, SegHead, MaskedPooling, ViewAggregator, FiLM, RegressionHead
from .config import TrainConfig, VIEWS, MEASUREMENTS


class SingleViewPipeline(nn.Module):
    """
    One camera view through the full pipeline.
    Input : normal_sil   [B, 4, H, W]   (normal map + silhouette)
            height_weight [B, 2]
    Output: measurements [B, 26]
            seg_logits   [B, K, 64, 64]
    """
    def __init__(self, cfg):
        super().__init__()
        self.backbone    = Backbone(cfg.backbone)
        self.seg_head    = SegHead(cfg.num_seg_classes)
        self.masked_pool = MaskedPooling(cfg.num_seg_classes, cfg.region_dim)
        self.view_agg    = ViewAggregator(self.masked_pool.out_dim, cfg.embed_dim)
        self.film        = FiLM(cfg.embed_dim)
        self.head        = RegressionHead(cfg.embed_dim, len(MEASUREMENTS), dropout=0.0)

    def forward(self, normal_sil, height_weight):
        # Backbone
        feat_64, feat_32, F_map = self.backbone(normal_sil)

        # Seg Head
        seg_logits = self.seg_head(F_map, feat_32, feat_64)

        # Masked Pooling
        view_feat = self.masked_pool(F_map, seg_logits)

        # View Aggregator (single view — unsqueeze/squeeze the V dim)
        global_embed = self.view_agg(view_feat.unsqueeze(1)).squeeze(1)

        # FiLM
        conditioned = self.film(global_embed, height_weight)

        # Regression
        measurements = self.head(conditioned)

        return measurements, seg_logits


def export_singleview(out_path: str, img_size: int = 256):
    cfg = TrainConfig()
    model = SingleViewPipeline(cfg)
    model.eval()

    dummy_img = torch.zeros(1, 4, img_size, img_size)
    dummy_hw  = torch.zeros(1, 2)

    print(f"Exporting single-view model to {out_path}")
    torch.onnx.export(
        model,
        (dummy_img, dummy_hw),
        out_path,
        input_names=["normal_sil", "height_weight"],
        output_names=["measurements", "seg_logits"],
        dynamic_axes={
            "normal_sil":    {0: "batch"},
            "height_weight": {0: "batch"},
            "measurements":  {0: "batch"},
            "seg_logits":    {0: "batch"},
        },
        opset_version=17,
    )
    print(f"Done.  netron {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="ml/model_singleview.onnx")
    parser.add_argument("--img_size", type=int, default=256)
    args = parser.parse_args()
    export_singleview(args.out, args.img_size)
