import os
import random
import shutil
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[3]
_DATASET = _REPO_ROOT / "data" / "dataset"

# ===== 参数与路径配置 =====
train_dir = str(_DATASET / "images" / "train")  # 训练集图片（源目录）
val_dir = str(_DATASET / "images" / "val")  # 验证集图片（目标目录）；可按需修改
val_ratio = 0.20      # 比例，例如 20% 就写 0.20

os.makedirs(val_dir, exist_ok=True)

# 支持的图片格式
valid_ext = (".jpg", ".jpeg", ".png")

# 读取训练集图片
images = [f for f in os.listdir(train_dir) if f.lower().endswith(valid_ext)]
images.sort(key=lambda x: int(os.path.splitext(x)[0]))

# 统计总数
total_count = len(images)

# 按比例计算验证集数量（四舍五入）
val_count = round(total_count * val_ratio)

# 防止比例太小或太大导致报错
if val_count < 1:
    raise ValueError(f"按照当前比例 {val_ratio} 计算，验证集数量小于 1，请调大比例。")

if val_count >= total_count:
    raise ValueError(f"按照当前比例 {val_ratio} 计算，验证集数量达到或超过训练集总数，请调小比例。")

# 固定随机种子，保证每次结果一致
random.seed(42)

# 随机抽取
val_images = random.sample(images, val_count)

# 移动到 val
for img in val_images:
    src = os.path.join(train_dir, img)
    dst = os.path.join(val_dir, img)
    shutil.move(src, dst)

print(f"原训练集图片总数: {total_count}")
print(f"设置比例: {val_ratio * 100:.1f}%")
print(f"移动到 val 的图片数量: {val_count}")
print(f"已完成，图片已移动到: {val_dir}")