"""
训练编排引擎 — 仅非交互模式，供 GUI 通过子进程调用。

入口：python gui/train_engine.py --no-interactive --mode 1 ...
"""
import os
import sys
import tempfile
import yaml
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

from core.config import TrainConfig
from core.train_logger import append_train_log, append_full_val_log
from core.training import (
    list_experiments, build_train_kwargs,
    get_class_names_from_data_yaml, get_val_labels_dir,
    count_val_label_stats, get_val_metrics,
)

# ── 国际化支持 ──────────────────────────────────────────────

_LOCALE_DIR = Path(__file__).resolve().parent.parent / "locales"

from core.i18n import load_locale, t as _t

_loc: dict = {}


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


# ── 数据增强 & 数据集与验证 ──────────────────────────────
# build_train_kwargs, get_class_names_from_data_yaml, get_val_labels_dir,
# count_val_label_stats, get_val_metrics imported from core.training


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
    _loc = load_locale(_LOCALE_DIR, args.lang)
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
