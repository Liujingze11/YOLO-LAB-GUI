"""
All paths are derived from the repository root (parent of scripts/).
Works on any machine after you clone or move the project.
"""
from pathlib import Path

# Repository root: .../yolo_lab_gui
REPO_ROOT = Path(__file__).resolve().parent.parent

DATA_YAML = str(REPO_ROOT / "data.yaml")
MODEL_FILE = str(REPO_ROOT / "pretrained_models" / "yolov8n-seg.pt")
RESULTS_DIR = str(REPO_ROOT / "outputs" / "results")
LOG_DIR = str(REPO_ROOT / "outputs" / "logs")

PREDICT_DIR = str(REPO_ROOT / "outputs" / "predict")
# Default “best” checkpoint for inference demos; change if you prefer another run.
BEST_SEG_MODEL = str(
    REPO_ROOT
    / "outputs"
    / "results"
    / "seg_dataset_all_pro_random__aug_e150_b16"
    / "weights"
    / "best.pt"
)
TEST_IMAGES_DIR = str(REPO_ROOT / "data" / "dataset" / "images" / "test")
