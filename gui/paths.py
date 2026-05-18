"""
All paths are derived from the repository root (parent of gui/).
Works on any machine after you clone or move the project.

Pretrained base models (e.g. yolov8n-seg.pt) use short names so that
ultralytics auto-downloads them into its cache on first use.
"""
from pathlib import Path

# Repository root: .../yolo_lab_gui
REPO_ROOT = Path(__file__).resolve().parent.parent

DATA_YAML = str(REPO_ROOT / "data.yaml")
# Short name → ultralytics auto-downloads to ~/.config/Ultralytics/
MODEL_FILE = "yolov8n-seg.pt"
RESULTS_DIR = str(REPO_ROOT / "outputs" / "results")
LOG_DIR = str(REPO_ROOT / "outputs" / "logs")

PREDICT_DIR = str(REPO_ROOT / "outputs" / "predict")
# No default best checkpoint — pick your trained model in the GUI.
BEST_SEG_MODEL = ""
TEST_IMAGES_DIR = str(REPO_ROOT / "data" / "dataset" / "images" / "test")
