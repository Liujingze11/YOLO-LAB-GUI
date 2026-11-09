"""Training log CSV management — shared by GUI and CLI."""
import os
import csv
from datetime import datetime


def get_timestamp() -> str:
    """Return current time as YYYY-MM-DD HH:MM:SS."""
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_log_dir(log_dir: str):
    """Create log directory if it does not exist."""
    os.makedirs(log_dir, exist_ok=True)


# ── train_log.csv ──────────────────────────────────────────


def ensure_train_csv_header(csv_path: str):
    """Create train_log.csv with headers if it does not exist."""
    if not os.path.exists(csv_path):
        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time",
                "mode",
                "status",
                "experiment_name",
                "model_file",
                "data_yaml",
                "epochs",
                "imgsz",
                "batch",
                "device",
                "save_dir",
                "best_pt",
                "last_pt",
                "notes",
            ])


def append_train_log(config, mode: str, status: str, notes: str = ""):
    """Append a row to train_log.csv."""
    ensure_log_dir(config.log_dir)
    csv_path = os.path.join(config.log_dir, "train_log.csv")
    ensure_train_csv_header(csv_path)

    with open(csv_path, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            get_timestamp(),
            mode,
            status,
            config.experiment_name,
            config.model_file,
            config.data_yaml,
            config.epochs,
            config.imgsz,
            config.batch,
            config.device,
            config.save_dir,
            config.best_pt,
            config.last_pt,
            notes,
        ])


# ── result_summary_log.csv ──────────────────────────────────


def ensure_result_summary_csv_header(csv_path: str):
    """Create result_summary_log.csv with headers if it does not exist."""
    if not os.path.exists(csv_path):
        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time",
                "mode",
                "experiment_name",
                "best_pt",
                "images",
                "instances",
                "box_p",
                "box_r",
                "box_map50",
                "box_map50_95",
                "mask_p",
                "mask_r",
                "mask_map50",
                "mask_map50_95",
                "notes",
            ])


def append_result_summary_log(config, mode: str, summary: dict, notes: str = ""):
    """Append a summary row to result_summary_log.csv."""
    ensure_log_dir(config.log_dir)
    csv_path = os.path.join(config.log_dir, "result_summary_log.csv")
    ensure_result_summary_csv_header(csv_path)

    with open(csv_path, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            get_timestamp(),
            mode,
            config.experiment_name,
            config.best_pt,
            summary.get("images", ""),
            summary.get("instances", ""),
            summary.get("box_p", ""),
            summary.get("box_r", ""),
            summary.get("box_map50", ""),
            summary.get("box_map50_95", ""),
            summary.get("mask_p", ""),
            summary.get("mask_r", ""),
            summary.get("mask_map50", ""),
            summary.get("mask_map50_95", ""),
            notes,
        ])


# ── result_per_class_log.csv ────────────────────────────────


def ensure_result_per_class_csv_header(csv_path: str):
    """Create result_per_class_log.csv with headers if it does not exist."""
    if not os.path.exists(csv_path):
        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time",
                "mode",
                "experiment_name",
                "best_pt",
                "class_id",
                "class_name",
                "images",
                "instances",
                "box_p",
                "box_r",
                "box_map50",
                "box_map50_95",
                "mask_p",
                "mask_r",
                "mask_map50",
                "mask_map50_95",
                "notes",
            ])


def append_result_per_class_log(config, mode: str, class_rows: list, notes: str = ""):
    """Append per-class rows to result_per_class_log.csv."""
    ensure_log_dir(config.log_dir)
    csv_path = os.path.join(config.log_dir, "result_per_class_log.csv")
    ensure_result_per_class_csv_header(csv_path)

    with open(csv_path, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for row in class_rows:
            writer.writerow([
                get_timestamp(),
                mode,
                config.experiment_name,
                config.best_pt,
                row.get("class_id", ""),
                row.get("class_name", ""),
                row.get("images", ""),
                row.get("instances", ""),
                row.get("box_p", ""),
                row.get("box_r", ""),
                row.get("box_map50", ""),
                row.get("box_map50_95", ""),
                row.get("mask_p", ""),
                row.get("mask_r", ""),
                row.get("mask_map50", ""),
                row.get("mask_map50_95", ""),
                notes,
            ])


# ── Metric extraction ───────────────────────────────────────


def extract_seg_val_metrics(metrics, class_image_counts=None, class_instance_counts=None):
    """Extract summary and per-class metrics from Ultralytics model.val() result.

    Returns (summary_dict, per_class_rows_list).
    """
    class_image_counts = class_image_counts or {}
    class_instance_counts = class_instance_counts or {}

    mean_vals = metrics.mean_results()

    summary = {
        "images": sum(class_image_counts.values()) if class_image_counts else "",
        "instances": sum(class_instance_counts.values()) if class_instance_counts else "",
        "box_p": mean_vals[0] if len(mean_vals) > 0 else "",
        "box_r": mean_vals[1] if len(mean_vals) > 1 else "",
        "box_map50": mean_vals[2] if len(mean_vals) > 2 else "",
        "box_map50_95": mean_vals[3] if len(mean_vals) > 3 else "",
        "mask_p": mean_vals[4] if len(mean_vals) > 4 else "",
        "mask_r": mean_vals[5] if len(mean_vals) > 5 else "",
        "mask_map50": mean_vals[6] if len(mean_vals) > 6 else "",
        "mask_map50_95": mean_vals[7] if len(mean_vals) > 7 else "",
    }

    per_class_rows = []
    names = metrics.names or {}

    def _is_valid_class(cname):
        if cname is None:
            return False
        s = str(cname).strip().lower()
        return s not in {"none", "", "background", "__background__"}

    valid_classes = [
        (cid, cname)
        for cid, cname in names.items()
        if _is_valid_class(cname)
    ]

    for idx, (class_id, class_name) in enumerate(valid_classes):
        try:
            vals = metrics.class_result(idx)
        except Exception:
            vals = []

        row = {
            "class_id": class_id,
            "class_name": class_name,
            "images": class_image_counts.get(class_name, 0),
            "instances": class_instance_counts.get(class_name, 0),
            "box_p": vals[0] if len(vals) > 0 else "",
            "box_r": vals[1] if len(vals) > 1 else "",
            "box_map50": vals[2] if len(vals) > 2 else "",
            "box_map50_95": vals[3] if len(vals) > 3 else "",
            "mask_p": vals[4] if len(vals) > 4 else "",
            "mask_r": vals[5] if len(vals) > 5 else "",
            "mask_map50": vals[6] if len(vals) > 6 else "",
            "mask_map50_95": vals[7] if len(vals) > 7 else "",
        }
        per_class_rows.append(row)

    return summary, per_class_rows


def append_full_val_log(config, mode: str, metrics, class_image_counts=None,
                        class_instance_counts=None, notes: str = ""):
    """Run validation logging: extract metrics, then append summary + per-class CSV rows."""
    summary, per_class_rows = extract_seg_val_metrics(
        metrics,
        class_image_counts=class_image_counts,
        class_instance_counts=class_instance_counts,
    )
    append_result_summary_log(config, mode, summary, notes)
    append_result_per_class_log(config, mode, per_class_rows, notes)
