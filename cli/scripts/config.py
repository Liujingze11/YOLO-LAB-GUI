from dataclasses import dataclass
import os
from paths import DATA_YAML, MODEL_FILE, RESULTS_DIR, LOG_DIR

@dataclass
class TrainConfig:

    # ===== 路径相关 =====
    data_yaml: str = DATA_YAML # data.yaml 配置文件路径
    model_file: str = MODEL_FILE # 初始加载的模型权重路径（如 yolov8n.pt、best.pt、last.pt）
    results_dir: str = RESULTS_DIR   # 所有实验结果保存的根目录
    log_dir: str = LOG_DIR   # 日志保存目录

    # ===== 超参数 =====
    epochs: int = 100   # 训练轮数
    imgsz: int = 640    # 输入图片尺寸
    batch: int = 8  # 每批次训练图片数量
    device: int = 0 # 使用的设备，0 表示第1块 GPU


    experiment_name: str = "seg_dataset771_random__aug_e100"    # 当前实验名称

    # ===== 数据增强相关 =====
    use_augment: bool = True
    hsv_h: float = 0.015
    hsv_s: float = 0.7
    hsv_v: float = 0.4
    degrees: float = 0.0
    translate: float = 0.1
    scale: float = 0.5
    shear: float = 0.0
    perspective: float = 0.0
    flipud: float = 0.0
    fliplr: float = 0.5
    mosaic: float = 1.0
    mixup: float = 0.0
    copy_paste: float = 0.0


    @property
    def save_dir(self) -> str:
        """
        本次实验结果的保存目录
        """
        return os.path.join(self.results_dir, self.experiment_name)

    @property
    def last_pt(self) -> str:
        """
        本次训练中断训练权重文件 last.pt 的路径
        """
        return os.path.join(self.save_dir, "weights", "last.pt")

    @property
    def best_pt(self) -> str:
        """
        本次实验最佳权重文件 best.pt 的路径
        """
        return os.path.join(self.save_dir, "weights", "best.pt")
    