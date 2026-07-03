"""Unified TrainConfig dataclass + user config file management.

Shared across YOLO-LAB-CLI, YOLO-LAB-GUI, and YOLO-LAB.
"""
import os
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path

from core.device import get_default_device


@dataclass
class TrainConfig:
    # === paths (set by each repo's entry point) ===
    data_yaml: str = ""
    model_file: str = ""
    results_dir: str = ""
    log_dir: str = ""

    # === hyperparameters ===
    epochs: int = 150
    imgsz: int = 640
    batch: int = 16
    device: str = field(default_factory=get_default_device)
    lr0: float = 0.0005
    close_mosaic: int = 10
    multi_scale: float = 0.5

    experiment_name: str = "experiment"

    # === data augmentation ===
    use_augment: bool = True
    hsv_h: float = 0.015
    hsv_s: float = 0.7
    hsv_v: float = 0.4
    degrees: float = 0.0
    translate: float = 0.1
    scale: float = 0.5
    shear: float = 0.0
    perspective: float = 0.0
    flipud: float = 0.0
    fliplr: float = 0.5
    mosaic: float = 1.0
    mixup: float = 0.0
    copy_paste: float = 0.0

    @property
    def save_dir(self) -> str:
        return os.path.join(self.results_dir, self.experiment_name)

    @property
    def last_pt(self) -> str:
        return os.path.join(self.save_dir, "weights", "last.pt")

    @property
    def best_pt(self) -> str:
        return os.path.join(self.save_dir, "weights", "best.pt")


# ── User config file (~/.yolo-lab/config.yaml) ──

_USER_CONFIG_DIR = Path.home() / ".yolo-lab"
_USER_CONFIG_PATH = _USER_CONFIG_DIR / "config.yaml"


def load_user_config() -> dict | None:
    """Load user config from ~/.yolo-lab/config.yaml.  Returns None if not found."""
    if not _USER_CONFIG_PATH.is_file():
        return None
    try:
        with open(_USER_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def save_user_config(cfg: TrainConfig) -> None:
    """Save TrainConfig to ~/.yolo-lab/config.yaml."""
    _USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    d = {k: v for k, v in asdict(cfg).items() if not k.startswith("_")}
    with open(_USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(d, f, allow_unicode=True, default_flow_style=False)


def merge_config(base: TrainConfig, overrides: dict) -> TrainConfig:
    """Apply overrides dict onto a TrainConfig, returning a NEW TrainConfig."""
    d = asdict(base)
    for k, v in overrides.items():
        if v is not None and k in d:
            d[k] = v
    return TrainConfig(**d)


def load_effective_config(cli_args: dict | None = None) -> TrainConfig:
    """Merge: defaults → ~/.yolo-lab/config.yaml → CLI args."""
    cfg = TrainConfig()
    file_cfg = load_user_config()
    if file_cfg:
        cfg = merge_config(cfg, file_cfg)
    if cli_args:
        cfg = merge_config(cfg, cli_args)
    return cfg
