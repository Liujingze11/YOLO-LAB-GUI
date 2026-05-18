import os
os.environ["MPLBACKEND"] = "Agg"  # 必须在 import matplotlib 之前设置，防止 FT2Font 字体加载错误

import yaml
import shutil   # 用于删除临时验证结果文件夹
import argparse
from ultralytics import YOLO
from config import TrainConfig
from train_logger import append_train_log, append_full_val_log

# =========================
# 训练配置对象
# =========================
CONFIG = TrainConfig()  # 配置了训练时需要使用的路径、模型和超参数

# =========================
# 工具函数
# =========================
def ask_confirm_train(mode, pt_path, config):
    """
    信息验证：在真正训练前打印关键信息，让用户手动确认。
    """
    print("\n------------------------------")
    print(f"即将执行：{mode}")
    print(f"当前使用的 PT 文件：{pt_path}")
    print(f"数据配置文件      ：{config.data_yaml}")
    print(f"实验名称          ：{config.experiment_name}")
    print(f"训练轮数 epochs   ：{config.epochs}")
    print("------------------------------")

    confirm = input("请确认是否继续？输入 y 继续，其他任意键取消：").strip().lower()
    if confirm != "y":
        print("\n已取消本次训练。")
        return False
    return True

def list_experiments(results_dir):
    """
    扫描 results_dir 目录下的所有子文件夹，获取历史实验文件夹列表。

    参数：
    results_dir: YOLO 训练结果保存目录
    """
    if not os.path.exists(results_dir):
        print(f"\n结果目录不存在：{results_dir}")
        return []

    folders = []
    # 遍历结果目录中的所有内容
    for name in os.listdir(results_dir):
        full_path = os.path.join(results_dir, name)
        if os.path.isdir(full_path):
            folders.append(name)

    folders.sort()  # 对实验名称排序，方便展示
    return folders


# =========================
# 命令行函数
# =========================
def parse_args():
    """
    解析命令行参数，允许用户在运行 Python 脚本时临时修改训练参数。

    示例：
    python train.py --epochs 200 --batch 8 --device 0 --name exp_test
    """
    parser = argparse.ArgumentParser(description="YOLO training script")

    parser.add_argument("--epochs", type=int, default=None, help="训练轮数")
    parser.add_argument("--imgsz", type=int, default=None, help="输入图片尺寸")
    parser.add_argument("--batch", type=int, default=None, help="每批次训练图片数量")
    parser.add_argument("--device", type=str, default=None, help="训练设备，如 0 / 0,1 / cpu")
    parser.add_argument("--name", type=str, default=None, help="实验名称")

    return parser.parse_args()


def override_config_from_args(config, args):
    """
    使用命令行参数覆盖默认配置。

    参数：
    config: 默认配置对象
    args: 命令行参数对象

    返回：
    修改后的 config
    """
    if args.epochs is not None:
        config.epochs = args.epochs
    if args.imgsz is not None:
        config.imgsz = args.imgsz
    if args.batch is not None:
        config.batch = args.batch
    if args.device is not None:
        config.device = args.device
    if args.name is not None:
        config.experiment_name = args.name

    return config


# =========================
# 数据增强
# =========================
def ask_use_augment(config):
    """
    训练前询问本次是否启用数据增强。
    """
    print("\n------------------------------")
    print("数据增强设置")
    print(f"当前默认值：{'开启' if config.use_augment else '关闭'}")
    print("------------------------------")

    choice = input("是否启用数据增强？输入 y 开启，n 关闭，直接回车使用默认值：").strip().lower()

    if choice == "y":
        return True
    elif choice == "n":
        return False
    else:
        return config.use_augment
    
def build_train_kwargs(config, use_augment):
    """
    统一构造 model.train() 的参数。
    如果 use_augment=True，则把增强参数也一起传进去。

    参数：
    config: 训练配置对象
    use_augment: 是否启用数据增强

    返回：
    kwargs: 传给 YOLO 训练函数的参数字典
    """
    kwargs = {
        "data": config.data_yaml,
        "epochs": config.epochs,
        "imgsz": config.imgsz,
        "batch": config.batch,
        "device": config.device,
        "project": config.results_dir,
        "name": config.experiment_name,
        "plots": False  # 禁用内部绘图，防止触发 matplotlib FT2Font 字体加载错误
    }

    if use_augment:
        kwargs.update({
            "hsv_h": config.hsv_h,
            "hsv_s": config.hsv_s,
            "hsv_v": config.hsv_v,
            "degrees": config.degrees,
            "translate": config.translate,
            "scale": config.scale,
            "shear": config.shear,
            "perspective": config.perspective,
            "flipud": config.flipud,
            "fliplr": config.fliplr,
            "mosaic": config.mosaic,
            "mixup": config.mixup,
            "copy_paste": config.copy_paste,
        })

    return kwargs


# =========================
# 数据集与验证集处理
# =========================
def get_class_names_from_data_yaml(data_yaml_path):
    with open(data_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    names = data.get("names", {})

    if isinstance(names, list):
        return {i: name for i, name in enumerate(names)}
    elif isinstance(names, dict):
        return {int(k): v for k, v in names.items()}
    else:
        return {}
    

def get_val_labels_dir(data_yaml_path):
    with open(data_yaml_path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f)

    root_path = data.get("path", "")
    val_path = data.get("val", "")

    if not val_path:
        return None

    # 如果 val 是相对路径，且 yaml 中配置了 path，则先拼完整路径
    if root_path and not os.path.isabs(val_path):
        val_path = os.path.join(root_path, val_path)

    val_path = os.path.normpath(val_path)

    # 常见情况：.../images/val -> .../labels/val
    parts = val_path.split(os.sep)
    if "images" in parts:
        idx = parts.index("images")
        parts[idx] = "labels"
        return os.path.normpath(os.sep.join(parts))

    # 兜底方案
    parent_dir = os.path.dirname(os.path.dirname(val_path))
    val_name = os.path.basename(val_path)
    return os.path.join(parent_dir, "labels", val_name)


def count_val_label_stats(config):
    val_labels_dir = get_val_labels_dir(config.data_yaml)
    if not val_labels_dir or not os.path.exists(val_labels_dir):
        print(f"\n未找到 val 标签目录：{val_labels_dir}")
        return {}, {}

    class_names = get_class_names_from_data_yaml(config.data_yaml)

    class_image_counts = {}
    class_instance_counts = {}

    for class_id, class_name in class_names.items():
        class_image_counts[class_name] = 0
        class_instance_counts[class_name] = 0

    for file_name in os.listdir(val_labels_dir):
        if not file_name.endswith(".txt"):
            continue

        file_path = os.path.join(val_labels_dir, file_name)
        appeared_in_this_image = set()

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
            appeared_in_this_image.add(class_name)

        for class_name in appeared_in_this_image:
            class_image_counts[class_name] = class_image_counts.get(class_name, 0) + 1

    return class_image_counts, class_instance_counts


def get_val_metrics(best_pt_path, config):
    model = YOLO(best_pt_path)


    val_name = f"{config.experiment_name}_tmp_val"
    val_dir = os.path.join(config.results_dir, val_name)
    
    try:
        metrics = model.val(
            data=config.data_yaml,
            imgsz=config.imgsz,
            batch=config.batch,
            device=config.device,
            plots=False,
            save_txt=False,
            save_json=False,
            visualize=False,
            project=config.results_dir,
            name=val_name
        )
        return metrics

    finally:
        shutil.rmtree(val_dir, ignore_errors=True)


def log_validation_result(config, mode, notes=""):
    if not os.path.exists(config.best_pt):
        print(f"\n未找到 best.pt，无法记录验证结果：{config.best_pt}")
        return

    try:
        metrics = get_val_metrics(config.best_pt, config)
        class_image_counts, class_instance_counts = count_val_label_stats(config)

        append_full_val_log(
            config=config,
            mode=mode,
            metrics=metrics,
            class_image_counts=class_image_counts,
            class_instance_counts=class_instance_counts,
            notes=notes  
        )
        print("\n验证结果已记录到日志。")

    except Exception as e:
        print(f"\n记录验证结果失败：{e}")


# =========================
# 训练流程
# =========================

# # ===== 模式1：开启一个新的训练 =====
def start_new_training(config):

    if not ask_confirm_train("模式1 - 开始新训练", config.model_file, config):
        return
    
    use_augment = ask_use_augment(config)
    append_train_log(config, mode="new_train", status="started", notes=f"开始新训练，数据增强={'开启' if use_augment else '关闭'}")

    try:
        model = YOLO(config.model_file)
        train_kwargs = build_train_kwargs(config, use_augment)
        model.train(**train_kwargs)

        append_train_log(config, mode="new_train", status="finished", notes=f"训练完成，数据增强={'开启' if use_augment else '关闭'}")
        log_validation_result(config, mode="new_train", notes="训练完成后的验证结果")

    except Exception as e:
        # 训练权重已由 ultralytics 自动保存，此处异常通常来自训练结束后的内部验证阶段
        if os.path.exists(config.best_pt):
            append_train_log(config, mode="new_train", status="finished",
                           notes=f"训练完成但内部验证失败: {e}")
            print(f"\n训练已完成（权重已保存），但内部验证失败：{e}")
            # 尝试用日志记录模块再次验证
            log_validation_result(config, mode="new_train", notes=f"内部验证失败后的重试验证。原错误: {e}")
        else:
            append_train_log(config, mode="new_train", status="failed", notes=str(e))
            print(f"\n训练失败：{e}")


# # ===== 模式2：继续上次中断的训练 =====
def resume_training(config):
    if not os.path.exists(config.last_pt):
        print(f"\n没有找到上次中断训练的权重文件：{config.last_pt}")

        choice = input("是否改为开启新的训练？输入 y 继续，其他任意键取消：").strip().lower()
        if choice == "y":
            start_new_training(config)
        else:
            print("已取消操作。")
        return

    if not ask_confirm_train("继续上次训练", config.last_pt, config):
        return

    append_train_log(config, mode="resume_train", status="started", notes="继续上次训练")

    try:
        model = YOLO(config.last_pt)
        model.train(resume=True)

        append_train_log(config, mode="resume_train", status="finished", notes="继续训练完成")
        log_validation_result(config, mode="resume_train", notes="继续训练后的验证结果")

    except Exception as e:
        append_train_log(config, mode="resume_train", status="failed", notes=str(e))
        print(f"\n继续训练失败：{e}")

# # ===== 模式3：基于历史实验的 best.pt 开启新训练 =====
def train_from_previous_best(config):
    folders = list_experiments(config.results_dir)

    if not folders:
        print("\n没有找到任何历史实验文件夹。")
        return

    print("\n检测到以下历史实验：")
    for i, folder in enumerate(folders, 1):
        print(f"{i} - {folder}")

    choice = input("请选择要作为基础模型的实验编号：").strip()

    if not choice.isdigit():
        print("输入无效，已取消。")
        return

    idx = int(choice) - 1
    if idx < 0 or idx >= len(folders):
        print("编号超出范围，已取消。")
        return

    selected_exp = folders[idx]
    selected_best_pt = os.path.join(config.results_dir, selected_exp, "weights", "best.pt")

    if not os.path.exists(selected_best_pt):
        print(f"\n该实验下没有找到 best.pt：{selected_best_pt}")
        return

    print(f"\n你选择的实验是：{selected_exp}")

    if not ask_confirm_train("基于历史 best.pt 开启新训练", selected_best_pt, config):
        return

    use_augment = ask_use_augment(config)

    append_train_log(
        config,
        mode="train_from_best",
        status="started",
        notes=f"基于历史实验 {selected_exp} 开始训练，数据增强={'开启' if use_augment else '关闭'}"
    )

    try:
        model = YOLO(selected_best_pt)
        train_kwargs = build_train_kwargs(config, use_augment)
        model.train(**train_kwargs)

        append_train_log(
            config,
            mode="train_from_best",
            status="finished",
            notes=f"基于历史实验 {selected_exp} 的训练完成，数据增强={'开启' if use_augment else '关闭'}"
        )

        log_validation_result(
            config,
            mode="train_from_best",
            notes=f"基于历史实验 {selected_exp} 的验证结果"
        )

    except Exception as e:
        if os.path.exists(config.best_pt):
            append_train_log(config, mode="train_from_best", status="finished",
                           notes=f"训练完成但内部验证失败（基础实验: {selected_exp}）: {e}")
            print(f"\n训练已完成（权重已保存），但内部验证失败：{e}")
            log_validation_result(config, mode="train_from_best",
                                notes=f"内部验证失败后的重试验证（基础实验: {selected_exp}）。原错误: {e}")
        else:
            append_train_log(config, mode="train_from_best", status="failed",
                           notes=f"基础实验 {selected_exp}: {e}")
            print(f"\n训练失败：{e}")


# =========================
# 主程序入口
# =========================
def main():
    global CONFIG
    args = parse_args()
    CONFIG = override_config_from_args(CONFIG, args)

    print("请选择训练模式：")
    print("模式1 - 开启一个新的训练")
    print("模式2 - 继续上次中断的训练")
    print("模式3 - 基于历史实验的 best.pt 再次训练")
    choice = input("请输入 1、2 或 3，直接回车退出\n").strip()

    if choice == "1":
        start_new_training(CONFIG)
    elif choice == "2":
        resume_training(CONFIG)
    elif choice == "3":
        train_from_previous_best(CONFIG)
    else:
        print("输入无效，程序已退出。")


if __name__ == "__main__":
    main()