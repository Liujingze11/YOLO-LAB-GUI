"""
训练编排引擎 — 仅非交互模式，供 GUI 通过子进程调用。

入口：python gui/train_engine.py --no-interactive --mode 1 ...
"""
import os
import sys
import tempfile
import json
import yaml
import shutil
import argparse
from pathlib import Path

# 子进程入口 — 确保项目根在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# matplotlib 子进程兼容：非交互后端 + 防止损坏字体导致崩溃
if "MPLBACKEND" not in os.environ:
    os.environ["MPLBACKEND"] = "Agg"

import matplotlib.font_manager as _fm
_original_addfont = _fm.FontManager.addfont

def _safe_addfont(self, path):
    try:
        _original_addfont(self, path)
    except RuntimeError:
        pass  # 跳过 FreeType 无法解析的损坏字体文件

_fm.FontManager.addfont = _safe_addfont

from ultralytics import YOLO

from gui.config import TrainConfig
from gui.train_logger import append_train_log, append_full_val_log

# ── 国际化支持 ──────────────────────────────────────────────

_LOCALE_DIR = Path(__file__).resolve().parent.parent / "locales"

def _load_locale(lang: str) -> dict:
    path = _LOCALE_DIR / f"{lang}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _t(loc: dict, key: str, **kwargs) -> str:
    text = loc.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text

_loc: dict = {}


def list_experiments(results_dir):
    """扫描 results_dir 目录下的所有子文件夹，获取历史实验文件夹列表。"""
    if not os.path.exists(results_dir):
        return []
    folders = sorted(
        name for name in os.listdir(results_dir)
        if os.path.isdir(os.path.join(results_dir, name))
    )
    return folders


def override_config_from_args(config, args):
    """使用命令行参数覆盖默认配置。"""
    for attr in ("epochs", "imgsz", "batch", "device", "data_yaml",
                 "model_file", "results_dir", "log_dir"):
        val = getattr(args, attr, None)
        if val is not None:
            setattr(config, attr, val)
    if args.name is not None:
        config.experiment_name = args.name
    return config


def _resolve_data_yaml(data_yaml_path: str) -> str:
    """将 data.yaml 中的相对 path 解析为绝对路径，写入临时文件后返回其路径。"""
    yaml_dir = os.path.dirname(os.path.abspath(data_yaml_path))
    with open(data_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    path_val = data.get("path", "")
    if path_val and not os.path.isabs(path_val):
        data["path"] = os.path.normpath(os.path.join(yaml_dir, path_val))
        tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False, encoding="utf-8")
        yaml.dump(data, tmp, allow_unicode=True, default_flow_style=False)
        tmp.close()
        print(_t(_loc, "train.engine.fix_path", old=path_val, new=data['path']))
        return tmp.name
    return data_yaml_path


# ── 数据增强 ──────────────────────────────────────────────

def build_train_kwargs(config, use_augment):
    kwargs = {
        "data": config.data_yaml,
        "epochs": config.epochs,
        "imgsz": config.imgsz,
        "batch": config.batch,
        "device": config.device,
        "project": config.results_dir,
        "name": config.experiment_name,
        "exist_ok": True,  # 使用精确实验名，避免 YOLO 自动追加后缀
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


# ── 数据集与验证 ──────────────────────────────────────────

def get_class_names_from_data_yaml(data_yaml_path):
    with open(data_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)
    names = data.get("names", {})
    if isinstance(names, list):
        return {i: name for i, name in enumerate(names)}
    elif isinstance(names, dict):
        return {int(k): v for k, v in names.items()}
    return {}


def get_val_labels_dir(data_yaml_path):
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


def count_val_label_stats(config):
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


def get_val_metrics(best_pt_path, config):
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


def log_validation_result(config, mode, notes=""):
    if not os.path.exists(config.best_pt):
        print(_t(_loc, "train.engine.no_best_pt", path=config.best_pt))
        return
    try:
        metrics = get_val_metrics(config.best_pt, config)
        class_image_counts, class_instance_counts = count_val_label_stats(config)
        append_full_val_log(
            config=config, mode=mode, metrics=metrics,
            class_image_counts=class_image_counts,
            class_instance_counts=class_instance_counts,
            notes=notes,
        )
        print(_t(_loc, "train.engine.val_logged"))
    except Exception as e:
        print(_t(_loc, "train.engine.val_failed", err=str(e)))


# ── 训练执行（非交互）─────────────────────────────────────

def execute_new_training(config, use_augment: bool) -> None:
    append_train_log(config, mode="new_train", status="started",
                     notes=_t(_loc, "train.engine.log_started",
                              aug='开启' if use_augment else '关闭'))
    try:
        model = YOLO(config.model_file)
        train_kwargs = build_train_kwargs(config, use_augment)
        model.train(**train_kwargs)
        append_train_log(config, mode="new_train", status="finished",
                         notes=_t(_loc, "train.engine.log_finished",
                                  aug='开启' if use_augment else '关闭'))
        log_validation_result(config, mode="new_train", notes=_t(_loc, "train.engine.log_val"))
    except Exception as e:
        append_train_log(config, mode="new_train", status="failed", notes=str(e))
        raise


def execute_resume_training(config) -> None:
    append_train_log(config, mode="resume_train", status="started",
                     notes=_t(_loc, "train.engine.log_resume_started"))
    try:
        model = YOLO(config.last_pt)
        model.train(resume=True)
        append_train_log(config, mode="resume_train", status="finished",
                         notes=_t(_loc, "train.engine.log_resume_finished"))
        log_validation_result(config, mode="resume_train", notes=_t(_loc, "train.engine.log_resume_val"))
    except Exception as e:
        append_train_log(config, mode="resume_train", status="failed", notes=str(e))
        raise


def execute_train_from_previous_best(config, selected_exp: str, use_augment: bool) -> None:
    selected_best_pt = os.path.join(config.results_dir, selected_exp, "weights", "best.pt")
    if not os.path.exists(selected_best_pt):
        raise FileNotFoundError(_t(_loc, "train.engine.no_best_pt_found", path=selected_best_pt))
    append_train_log(config, mode="train_from_best", status="started",
                     notes=_t(_loc, "train.engine.log_finetune_started",
                              exp=selected_exp, aug='开启' if use_augment else '关闭'))
    try:
        model = YOLO(selected_best_pt)
        train_kwargs = build_train_kwargs(config, use_augment)
        model.train(**train_kwargs)
        append_train_log(config, mode="train_from_best", status="finished",
                         notes=_t(_loc, "train.engine.log_finetune_finished",
                                  exp=selected_exp, aug='开启' if use_augment else '关闭'))
        log_validation_result(config, mode="train_from_best",
                              notes=_t(_loc, "train.engine.log_finetune_val", exp=selected_exp))
    except Exception as e:
        append_train_log(config, mode="train_from_best", status="failed", notes=str(e))
        raise


def run_non_interactive(args):
    """根据命令行参数直接运行训练，不弹出任何交互提示。"""
    global _loc
    _loc = _load_locale(args.lang)
    config = TrainConfig()
    config = override_config_from_args(config, args)

    _original_data_yaml = config.data_yaml
    config.data_yaml = _resolve_data_yaml(config.data_yaml)

    try:
        mode = args.mode
        if mode is None:
            print(_t(_loc, "train.engine.no_mode"))
            sys.exit(1)

        use_augment = args.use_augment if args.use_augment is not None else config.use_augment

        if mode == 1:
            print(_t(_loc, "train.engine.new_start", name=config.experiment_name))
            print(_t(_loc, "train.engine.new_weights", model=config.model_file, epochs=config.epochs, imgsz=config.imgsz, batch=config.batch, device=config.device))
            print(_t(_loc, "train.engine.augment_on" if use_augment else "train.engine.augment_off"))
            execute_new_training(config, use_augment)

        elif mode == 2:
            if not os.path.exists(config.last_pt):
                print(_t(_loc, "train.engine.resume_fallback", path=config.last_pt))
                print(_t(_loc, "train.engine.new_weights", model=config.model_file, epochs=config.epochs, imgsz=config.imgsz, batch=config.batch, device=config.device))
                execute_new_training(config, use_augment)
            else:
                print(_t(_loc, "train.engine.resume_start", name=config.experiment_name))
                print(_t(_loc, "train.engine.resume_weights", path=config.last_pt))
                execute_resume_training(config)

        elif mode == 3:
            selected_exp = args.selected_exp
            if not selected_exp:
                print(_t(_loc, "train.engine.no_selected_exp"))
                sys.exit(1)
            print(_t(_loc, "train.engine.history_train", exp=selected_exp))
            print(_t(_loc, "train.engine.history_params", epochs=config.epochs, imgsz=config.imgsz, batch=config.batch, device=config.device))
            print(_t(_loc, "train.engine.augment_on" if use_augment else "train.engine.augment_off"))
            execute_train_from_previous_best(config, selected_exp, use_augment)
    finally:
        if config.data_yaml != _original_data_yaml and os.path.exists(config.data_yaml):
            os.unlink(config.data_yaml)


# ── 子进程入口 ────────────────────────────────────────────

def parse_args():
    parser = argparse.ArgumentParser(description="YOLO training engine (non-interactive)")
    parser.add_argument("--epochs", type=int, default=None)
    parser.add_argument("--imgsz", type=int, default=None)
    parser.add_argument("--batch", type=int, default=None)
    parser.add_argument("--device", type=str, default=None)
    parser.add_argument("--name", type=str, default=None)
    parser.add_argument("--data-yaml", type=str, default=None)
    parser.add_argument("--model-file", type=str, default=None)
    parser.add_argument("--results-dir", type=str, default=None)
    parser.add_argument("--log-dir", type=str, default=None)
    parser.add_argument("--no-interactive", action="store_true")
    parser.add_argument("--mode", type=int, choices=[1, 2, 3], default=None)
    parser.add_argument("--use-augment", action="store_true", default=None, dest="use_augment")
    parser.add_argument("--no-augment", action="store_false", default=None, dest="use_augment")
    parser.add_argument("--selected-exp", type=str, default=None)
    parser.add_argument("--lang", default="zh", help="Language code (zh/en/fr/es)")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    run_non_interactive(args)
