import os
import shutil
from pathlib import Path

# 仓库根目录下的默认数据集布局（与根目录 data.yaml 中 path: data/dataset 一致）
_REPO_ROOT = Path(__file__).resolve().parents[3]
_DATASET = _REPO_ROOT / "data" / "dataset"

# ===== 参数与路径配置 =====
train_dir = str(_DATASET / "images" / "train")  # 训练集图片（源目录）
val_dir = str(_DATASET / "images" / "val")  # 验证集图片（目标目录）；可按需改成任意路径
times = 5   # 倍数

# 创建目标文件夹
os.makedirs(val_dir, exist_ok=True) 

# 读取训练集图片
images = [f for f in os.listdir(train_dir) if f.lower().endswith(".jpg")]
images.sort(key=lambda x: int(os.path.splitext(x)[0]))

# ===== 照片移动 =====
for img in images:
    num = int(os.path.splitext(img)[0])
    if num % times == 0:
        src = os.path.join(train_dir, img)
        dst = os.path.join(val_dir, img)
        shutil.move(src, dst)

print("已将 5 的倍数编号图片移动到 val")