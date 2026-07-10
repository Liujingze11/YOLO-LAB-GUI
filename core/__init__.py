"""YOLO-LAB shared core — identical across CLI, GUI, and LAB repos."""
from core.config import TrainConfig, load_user_config, save_user_config, merge_config, load_effective_config
from core.train_logger import append_train_log, append_full_val_log, extract_seg_val_metrics
from core.training import build_train_kwargs, list_experiments
from core.device import get_default_device, get_available_devices
from core.i18n import load_locale, t
from core import paths
