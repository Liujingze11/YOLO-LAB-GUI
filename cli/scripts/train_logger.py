import os
import csv
from datetime import datetime


def get_timestamp() -> str:
    """
    获取当前时间字符串，用于时间戳
    """
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_log_dir(log_dir: str):
    """
    确保日志目录存在，如果目录不存在，就自动创建；

    参数：
        log_dir: 日志文件夹路径
    """
    os.makedirs(log_dir, exist_ok=True)


# =========================
# 训练流程日志 train_log.csv
# =========================
def ensure_train_csv_header(csv_path: str):
    """
    确保文件的存在；确保训练流程日志 CSV 文件的表头。
    
    参数：
        csv_path: train_log.csv 的完整路径
    """
    if not os.path.exists(csv_path):
        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time",              # 记录时间
                "mode",              # 当前模式，例如 train / resume 
                "status",            # 当前状态，例如 success / failed
                "experiment_name",   # 实验名称
                "model_file",        # 使用的模型文件路径
                "data_yaml",         # 数据集配置文件路径
                "epochs",            # 训练轮数
                "imgsz",             # 输入图像尺寸
                "batch",             # batch size
                "device",            # 使用的设备，例如 0 / cpu
                "save_dir",          # 本次实验结果保存目录
                "best_pt",           # best.pt 权重路径
                "last_pt",           # last.pt 权重路径
                "notes"              # 备注信息
            ])


def append_train_log(config, mode: str, status: str, notes: str = ""):
    """
    向训练流程日志中追加一行记录。
    
    参数：
        config: 训练配置对象，通常包含 experiment_name、model_file 等属性
        mode: 当前模式，例如 "train"、"resume"
        status: 当前状态，例如 "success"、"failed"
        notes: 备注信息，可选
    """
    ensure_log_dir(config.log_dir)  # 确保文件的存在

    # 确保文件的存在；确保训练流程日志 CSV 文件的表头。
    csv_path = os.path.join(config.log_dir, "train_log.csv")
    ensure_train_csv_header(csv_path)

    # # 以追加模式写入一行新记录
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
            notes
        ])

# =========================
# 训练结果日志：总结果（all）result_summary_log.csv
# =========================
def ensure_result_summary_csv_header(csv_path: str):
    """
    确保文件的存在；确保“总体验证结果”日志 CSV 文件存在表头。
    
    参数：
        csv_path: result_summary_log.csv 的完整路径
    """
    if not os.path.exists(csv_path):
        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time",              # 记录时间
                "mode",              # 当前模式，例如 val
                "experiment_name",   # 实验名称
                "best_pt",           # 对应的 best.pt 文件
                "images",            # 验证集中图像数
                "instances",         # 验证集中目标实例总数
                "box_p",             # 检测框 Precision
                "box_r",             # 检测框 Recall
                "box_map50",         # 检测框 mAP@0.5
                "box_map50_95",      # 检测框 mAP@0.5:0.95
                "mask_p",            # 分割掩码 Precision
                "mask_r",            # 分割掩码 Recall
                "mask_map50",        # 分割掩码 mAP@0.5
                "mask_map50_95",     # 分割掩码 mAP@0.5:0.95
                "notes"              # 备注信息
            ])


def append_result_summary_log(config, mode: str, summary: dict, notes: str = ""):
    """
    向“分类别验证结果”日志中追加多行记录。
    
    参数：
        config: 配置对象
        mode: 模式，例如 "val"
        class_rows: 每个类别对应的结果列表，列表中的每个元素都是一个字典
        notes: 备注
    """
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
            notes
        ])


# =========================
# 训练结果日志：分类别结果 result_per_class_log.csv
# =========================
def ensure_result_per_class_csv_header(csv_path: str):
    """
    确保“分类别验证结果”日志 CSV 文件存在表头。
    
    参数：
        csv_path: result_per_class_log.csv 的完整路径
    """
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
                "notes"
            ])


def append_result_per_class_log(config, mode: str, class_rows: list, notes: str = ""):
    """
    向“分类别验证结果”日志中追加多行记录。
    
    参数：
        config: 配置对象
        mode: 模式，例如 "val"
        class_rows: 每个类别对应的结果列表，列表中的每个元素都是一个字典
        notes: 备注
    """
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
                notes
            ])


# =========================
# 从 Ultralytics val 结果中提取指标
# =========================
def extract_seg_val_metrics(metrics, class_image_counts=None, class_instance_counts=None):
    """
    从 model.val() 返回的 metrics 对象中提取：
    1. 总结果 summary（all）
    2. 各类别结果 per_class

    参数：
        metrics: Ultralytics 的验证结果对象
        class_image_counts: 一个字典，记录每个类别出现在多少张图中
        class_instance_counts: 一个字典，记录每个类别有多少个实例
    """
    # 如果调用者没有传入统计信息，就用空字典代替
    class_image_counts = class_image_counts or {}
    class_instance_counts = class_instance_counts or {}

    # 获取总体平均指标
    # 对于分割任务，通常顺序是：
    # [box_p, box_r, box_map50, box_map50_95, mask_p, mask_r, mask_map50, mask_map50_95]
    mean_vals = metrics.mean_results()

    # 组织总结果字典
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
    
    # 用来保存每个类别的结果
    per_class_rows = []
    names = metrics.names or {}

    # 只保留真正有效的类别，过滤掉 None
    def is_valid_class_name(cname):
        if cname is None:
            return False
        s = str(cname).strip().lower()
        return s not in {"none", "", "background", "__background__"}

    valid_classes = [
        (cid, cname)
        for cid, cname in names.items()
        if is_valid_class_name(cname)
    ]

    # 按真实类别顺序去取 class_result(idx)
    for idx, (class_id, class_name) in enumerate(valid_classes):
        try:
            vals = metrics.class_result(idx)
        except Exception:
            vals = []

        row = {
            "class_id": class_id,   # 保留你原始的数据集类别编号
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


def append_full_val_log(config,mode: str,metrics,class_image_counts=None,class_instance_counts=None,notes: str = ""):
    """
    这是一个“总入口函数”，外部一般直接调用它即可。
    
    参数：
        config: 配置对象
        mode: 模式，一般是 "val"
        metrics: model.val() 返回的指标对象
        class_image_counts: 各类别图像数统计
        class_instance_counts: 各类别实例数统计
        notes: 备注
    """
        
    summary, per_class_rows = extract_seg_val_metrics(
        metrics,
        class_image_counts=class_image_counts,
        class_instance_counts=class_instance_counts
    )

    append_result_summary_log(config, mode, summary, notes)
    append_result_per_class_log(config, mode, per_class_rows, notes)