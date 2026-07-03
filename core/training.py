"""Shared training/validation logic used by both GUI and CLI."""
import os
import re
import yaml
import shutil
from pathlib import Path


def list_experiments(results_dir: str) -> list:
    if not os.path.exists(results_dir):
        return []
    return sorted(
        name for name in os.listdir(results_dir)
        if os.path.isdir(os.path.join(results_dir, name))
    )


def build_train_kwargs(config, use_augment: bool) -> dict:
    kwargs = {
        "data": config.data_yaml,
        "epochs": config.epochs,
        "imgsz": config.imgsz,
        "batch": config.batch,
        "device": config.device,
        "project": config.results_dir,
        "name": config.experiment_name,
        "exist_ok": True,
        "plots": True,
        "lr0": config.lr0,
        "close_mosaic": config.close_mosaic,
        "multi_scale": config.multi_scale,
    }
    if use_augment:
        kwargs.update({
            "hsv_h": config.hsv_h, "hsv_s": config.hsv_s, "hsv_v": config.hsv_v,
            "degrees": config.degrees, "translate": config.translate,
            "scale": config.scale, "shear": config.shear,
            "perspective": config.perspective, "flipud": config.flipud,
            "fliplr": config.fliplr, "mosaic": config.mosaic,
            "mixup": config.mixup, "copy_paste": config.copy_paste,
        })
    return kwargs


def get_class_names_from_data_yaml(data_yaml_path: str) -> dict:
    with open(data_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    names = data.get("names", {})
    if isinstance(names, list):
        return {i: name for i, name in enumerate(names)}
    elif isinstance(names, dict):
        return {int(k): v for k, v in names.items()}
    return {}


def get_val_labels_dir(data_yaml_path: str) -> str | None:
    with open(data_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    root_path = data.get("path", "")
    val_path = data.get("val", "")
    if not val_path:
        return None
    if root_path and not os.path.isabs(val_path):
        val_path = os.path.join(root_path, val_path)
    val_path = os.path.normpath(val_path)
    parts = val_path.split(os.sep)
    if "images" in parts:
        idx = parts.index("images")
        parts[idx] = "labels"
        return os.path.normpath(os.sep.join(parts))
    parent_dir = os.path.dirname(os.path.dirname(val_path))
    val_name = os.path.basename(val_path)
    return os.path.join(parent_dir, "labels", val_name)


def count_val_label_stats(config) -> tuple:
    val_labels_dir = get_val_labels_dir(config.data_yaml)
    if not val_labels_dir or not os.path.exists(val_labels_dir):
        return {}, {}
    class_names = get_class_names_from_data_yaml(config.data_yaml)
    class_image_counts = {name: 0 for name in class_names.values()}
    class_instance_counts = {name: 0 for name in class_names.values()}
    for file_name in os.listdir(val_labels_dir):
        if not file_name.endswith(".txt"):
            continue
        file_path = os.path.join(val_labels_dir, file_name)
        appeared = set()
        with open(file_path, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if line.strip()]
        for line in lines:
            parts = line.split()
            if len(parts) < 1:
                continue
            try:
                class_id = int(float(parts[0]))
            except ValueError:
                continue
            class_name = class_names.get(class_id, f"class_{class_id}")
            class_instance_counts[class_name] = class_instance_counts.get(class_name, 0) + 1
            appeared.add(class_name)
        for class_name in appeared:
            class_image_counts[class_name] = class_image_counts.get(class_name, 0) + 1
    return class_image_counts, class_instance_counts


def get_val_metrics(best_pt_path: str, config) -> object:
    from ultralytics import YOLO
    model = YOLO(best_pt_path)
    val_name = f"{config.experiment_name}_tmp_val"
    val_dir = os.path.join(config.results_dir, val_name)
    try:
        metrics = model.val(
            data=config.data_yaml, imgsz=config.imgsz, batch=config.batch,
            device=config.device, plots=False, save_txt=False, save_json=False,
            visualize=False, project=config.results_dir, name=val_name,
        )
        return metrics
    finally:
        shutil.rmtree(val_dir, ignore_errors=True)


def find_latest_experiment_dir(results_dir: str, experiment_name: str) -> str | None:
    """Find the latest auto-suffixed experiment directory.

    Ultralytics appends -N suffixes when experiment_name already exists.
    This function finds the directory with the highest suffix number.
    """
    if not os.path.exists(results_dir):
        return None

    pattern = re.compile(r'^' + re.escape(experiment_name) + r'(?:-(\d+))?$')

    best_dir = None
    best_suffix = -1

    for name in os.listdir(results_dir):
        full_path = os.path.join(results_dir, name)
        if not os.path.isdir(full_path):
            continue
        match = pattern.match(name)
        if match:
            suffix_str = match.group(1)
            suffix = int(suffix_str) if suffix_str else 0
            if suffix > best_suffix:
                best_suffix = suffix
                best_dir = name

    return best_dir


def log_validation_result(config, mode: str, notes: str = ""):
    """Run validation on best.pt and write results to CSV logs."""
    from core.train_logger import append_full_val_log

    if not os.path.exists(config.best_pt):
        print(f"No best.pt found at {config.best_pt}, skipping validation.")
        return

    try:
        metrics = get_val_metrics(config.best_pt, config)
        class_image_counts, class_instance_counts = count_val_label_stats(config)
        append_full_val_log(
            config=config, mode=mode, metrics=metrics,
            class_image_counts=class_image_counts,
            class_instance_counts=class_instance_counts, notes=notes,
        )
        print(f"Validation logged for {mode}")
    except Exception as e:
        print(f"Validation failed for {mode}: {e}")
