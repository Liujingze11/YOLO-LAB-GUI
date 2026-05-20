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

PRETRAINED_DIR = REPO_ROOT / "pretrained_models"

_MODEL_URL_BASE = "https://github.com/ultralytics/assets/releases/download"
_MODEL_URL_TAGS = {
    "v8": "v8.2.0",
    "v11": "v8.3.0",
    "v12": "v8.3.0",
}

MODEL_REGISTRY: list[tuple[str, str, str]] = [
    # (filename, display_name, tag_key, url)
    # --- Segmentation ---
    ("yolov8n-seg.pt",  "YOLOv8n-seg",  "v8"),
    ("yolov8s-seg.pt",  "YOLOv8s-seg",  "v8"),
    ("yolov8m-seg.pt",  "YOLOv8m-seg",  "v8"),
    ("yolov8l-seg.pt",  "YOLOv8l-seg",  "v8"),
    ("yolov8x-seg.pt",  "YOLOv8x-seg",  "v8"),
    ("yolo11n-seg.pt",  "YOLO11n-seg",  "v11"),
    ("yolo11s-seg.pt",  "YOLO11s-seg",  "v11"),
    ("yolo11m-seg.pt",  "YOLO11m-seg",  "v11"),
    ("yolo11l-seg.pt",  "YOLO11l-seg",  "v11"),
    ("yolo11x-seg.pt",  "YOLO11x-seg",  "v11"),
    ("yolo12n-seg.pt",  "YOLO12n-seg",  "v12"),
    ("yolo12s-seg.pt",  "YOLO12s-seg",  "v12"),
    ("yolo12m-seg.pt",  "YOLO12m-seg",  "v12"),
    ("yolo12l-seg.pt",  "YOLO12l-seg",  "v12"),
    ("yolo12x-seg.pt",  "YOLO12x-seg",  "v12"),
    # --- Detection ---
    ("yolov8n.pt",  "YOLOv8n",   "v8"),
    ("yolov8s.pt",  "YOLOv8s",   "v8"),
    ("yolov8m.pt",  "YOLOv8m",   "v8"),
    ("yolov8l.pt",  "YOLOv8l",   "v8"),
    ("yolov8x.pt",  "YOLOv8x",   "v8"),
    ("yolo11n.pt",  "YOLO11n",  "v11"),
    ("yolo11s.pt",  "YOLO11s",  "v11"),
    ("yolo11m.pt",  "YOLO11m",  "v11"),
    ("yolo11l.pt",  "YOLO11l",  "v11"),
    ("yolo11x.pt",  "YOLO11x",  "v11"),
]


def get_model_download_url(filename: str, tag_key: str) -> str:
    tag = _MODEL_URL_TAGS.get(tag_key, "v8.3.0")
    return f"{_MODEL_URL_BASE}/{tag}/{filename}"

PREDICT_DIR = str(REPO_ROOT / "outputs" / "predict")
# No default best checkpoint — pick your trained model in the GUI.
BEST_SEG_MODEL = ""
TEST_IMAGES_DIR = str(REPO_ROOT / "data" / "dataset" / "images" / "test")
