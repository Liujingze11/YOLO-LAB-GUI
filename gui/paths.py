"""
All paths are derived from the repository root (parent of gui/).
Works on any machine after you clone or move the project.

Pretrained base models (e.g. yolov8n-seg.pt) use short names so that
ultralytics auto-downloads them into its cache on first use.
"""
import os
import platform
import sys
from pathlib import Path

# Repository root: .../yolo_lab_gui
REPO_ROOT = Path(__file__).resolve().parent.parent


def is_frozen() -> bool:
    """True when running inside a PyInstaller bundle."""
    return getattr(sys, "frozen", False)


def get_user_data_dir() -> Path:
    """Platform-standard user data directory (YoloLab)."""
    app_name = "YoloLab"
    system = platform.system()
    if system == "Windows":
        base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    elif system == "Darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return base / app_name


def ensure_user_dirs() -> dict:
    """Create and return user data subdirectories."""
    data_dir = get_user_data_dir()
    dirs = {
        "models": data_dir / "models",
        "results": data_dir / "results",
        "logs": data_dir / "logs",
        "predict": data_dir / "predict",
        "gpu": data_dir / "gpu",
    }
    for d in dirs.values():
        d.mkdir(parents=True, exist_ok=True)
    return dirs

# Short name → ultralytics auto-downloads to ~/.config/Ultralytics/
MODEL_FILE = "yolov8n-seg.pt"
RESULTS_DIR = str(REPO_ROOT / "outputs" / "results")
LOG_DIR = str(REPO_ROOT / "outputs" / "logs")

PRETRAINED_DIR = REPO_ROOT / "pretrained_models"

PREDICT_DIR = str(REPO_ROOT / "outputs" / "predict")
# No default best checkpoint — pick your trained model in the GUI.
BEST_SEG_MODEL = ""
TEST_IMAGES_DIR = str(REPO_ROOT / "data" / "dataset" / "images" / "test")
