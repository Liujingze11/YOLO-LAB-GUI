from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

DATA_YAML = str(PROJECT_ROOT / "data.yaml")
MODEL_FILE = str(PROJECT_ROOT / "pretrained_models" / "yolov8n-seg.pt")
RESULTS_DIR = str(PROJECT_ROOT / "result")
LOG_DIR = str(PROJECT_ROOT / "train_logs")

PREDICT_DIR = str(PROJECT_ROOT / "predict")
BEST_SEG_MODEL = str(PROJECT_ROOT / "result" / "seg_dataset_all_pro_random__aug_e150_b16" / "weights" / "best.pt")
TEST_IMAGES_DIR = str(PROJECT_ROOT / "data" / "Source Data" / "datasets_all_pro" / "images" / "test")