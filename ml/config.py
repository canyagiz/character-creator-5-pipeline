MEASUREMENTS = [
    "height_cm",
    "neck_circ_cm", "chest_circ_cm", "waist_circ_cm", "hip_circ_cm",
    "mid_thigh_circ_cm", "calf_circ_cm", "bicep_circ_cm", "elbow_circ_cm",
    "forearm_circ_cm", "wrist_circ_cm",
    "shoulder_width_cm", "hip_width_cm",
    "upper_arm_length_cm", "forearm_length_cm", "total_arm_length_cm",
    "upper_leg_length_cm", "lower_leg_length_cm", "total_leg_length_cm",
    "seg_foot_cm", "seg_lower_leg_cm", "seg_upper_leg_cm",
    "seg_torso_cm", "seg_neck_cm", "seg_head_cm",
    "volume_L",
]

VIEWS = [
    "front", "back", "left", "right",
    "front_left", "front_right", "back_left", "back_right",
]

FLIP_VIEW_PAIRS = {
    "left": "right", "right": "left",
    "front_left": "front_right", "front_right": "front_left",
    "back_left": "back_right", "back_right": "back_left",
    "front": "front", "back": "back",
}


class TrainConfig:
    # paths
    data_root: str = "/content/renders"
    checkpoint_dir: str = "/content/checkpoints"

    # data
    img_size: int = 256
    val_split: float = 0.1
    num_workers: int = 2

    # model
    backbone: str = "efficientnet_b3"
    num_seg_classes: int = 15   # unique colors in seg masks (scanned from data)
    region_dim: int = 128       # per-region bottleneck before view aggregation
    embed_dim: int = 512        # view aggregation embedding
    dropout: float = 0.3

    # training
    batch_size: int = 8
    epochs: int = 100
    lr: float = 3e-4
    lr_backbone: float = 3e-5
    weight_decay: float = 1e-4
    warmup_epochs: int = 5
    grad_clip: float = 1.0

    # loss
    seg_loss_weight: float = 0.5   # λ: L_total = L_meas + λ * L_seg

    seed: int = 42
