import os
import random
import shutil
from pathlib import Path

# ===== 路径配置（与根目录 data.yaml 中 path: data/dataset 一致）=====
_REPO_ROOT = Path(__file__).resolve().parents[3]
base_dir = str(_REPO_ROOT / "data" / "dataset")

images_train_dir = os.path.join(base_dir, "images", "train")
images_val_dir   = os.path.join(base_dir, "images", "val")
images_test_dir  = os.path.join(base_dir, "images", "test")

labels_train_dir = os.path.join(base_dir, "labels", "train")
labels_val_dir   = os.path.join(base_dir, "labels", "val")
labels_test_dir  = os.path.join(base_dir, "labels", "test")

# ===== 比例配置 =====
val_ratio = 0.20   # 验证集比例
test_ratio = 0.10  # 测试集比例

# 固定随机种子，保证每次结果一致
random.seed(42)

# 支持的图片格式
valid_ext = (".jpg", ".jpeg", ".png")

# 创建目标文件夹
os.makedirs(images_val_dir, exist_ok=True)
os.makedirs(images_test_dir, exist_ok=True)
os.makedirs(labels_val_dir, exist_ok=True)
os.makedirs(labels_test_dir, exist_ok=True)

# =========================
# 读取 train 中的图片
# =========================
images = [f for f in os.listdir(images_train_dir) if f.lower().endswith(valid_ext)]

# 只保留“去掉后缀后文件名是纯数字”的图片
valid_images = []
for f in images:
    name_without_ext = os.path.splitext(f)[0]
    if name_without_ext.isdigit():
        valid_images.append(f)
    else:
        print(f"跳过非纯数字文件名图片: {f}")

# 按数字排序
valid_images.sort(key=lambda x: int(os.path.splitext(x)[0]))

# 总数
total_count = len(valid_images)

# 计算数量
val_count = round(total_count * val_ratio)
test_count = round(total_count * test_ratio)

# 合法性检查
if total_count == 0:
    raise ValueError("train 文件夹中没有可用图片。")

if val_count < 1:
    raise ValueError(f"val_ratio={val_ratio} 计算后验证集数量小于 1，请调大比例。")

if test_count < 1:
    raise ValueError(f"test_ratio={test_ratio} 计算后测试集数量小于 1，请调大比例。")

if val_count + test_count >= total_count:
    raise ValueError(
        f"val({val_count}) + test({test_count}) >= 总数({total_count})，请调小比例。"
    )

# =========================
# 随机划分
# =========================
# 先从 train 中随机抽出 val
val_images = random.sample(valid_images, val_count)

# 剩余图片中再抽 test
remaining_images = [img for img in valid_images if img not in val_images]
test_images = random.sample(remaining_images, test_count)

# =========================
# 统计信息
# =========================
moved_val_img_count = 0
moved_val_label_count = 0
missing_val_label_count = 0

moved_test_img_count = 0
moved_test_label_count = 0
missing_test_label_count = 0

# =========================
# 工具函数：移动图片和标签
# =========================
def move_files(image_list, target_images_dir, target_labels_dir):
    moved_img_count = 0
    moved_label_count = 0
    missing_label_count = 0

    for img in image_list:
        name_without_ext = os.path.splitext(img)[0]

        # 移动图片
        img_src = os.path.join(images_train_dir, img)
        img_dst = os.path.join(target_images_dir, img)

        if os.path.exists(img_src):
            shutil.move(img_src, img_dst)
            moved_img_count += 1
        else:
            print(f"警告：未找到图片文件 {img_src}")
            continue

        # 移动标签
        label_name = name_without_ext + ".txt"
        label_src = os.path.join(labels_train_dir, label_name)
        label_dst = os.path.join(target_labels_dir, label_name)

        if os.path.exists(label_src):
            shutil.move(label_src, label_dst)
            moved_label_count += 1
        else:
            print(f"警告：未找到对应标签文件 {label_src}")
            missing_label_count += 1

    return moved_img_count, moved_label_count, missing_label_count

# =========================
# 执行移动
# =========================
moved_val_img_count, moved_val_label_count, missing_val_label_count = move_files(
    val_images, images_val_dir, labels_val_dir
)

moved_test_img_count, moved_test_label_count, missing_test_label_count = move_files(
    test_images, images_test_dir, labels_test_dir
)

# ===== 输出结果 =====
print("\n===== 数据集划分完成 =====")
print(f"原 train 图片总数: {total_count}")

print(f"\n[验证集 val]")
print(f"设置比例: {val_ratio * 100:.1f}%")
print(f"计划移动图片数量: {val_count}")
print(f"实际移动图片数量: {moved_val_img_count}")
print(f"实际移动标签数量: {moved_val_label_count}")
print(f"缺失标签数量: {missing_val_label_count}")
print(f"图片目标路径: {images_val_dir}")
print(f"标签目标路径: {labels_val_dir}")

print(f"\n[测试集 test]")
print(f"设置比例: {test_ratio * 100:.1f}%")
print(f"计划移动图片数量: {test_count}")
print(f"实际移动图片数量: {moved_test_img_count}")
print(f"实际移动标签数量: {moved_test_label_count}")
print(f"缺失标签数量: {missing_test_label_count}")
print(f"图片目标路径: {images_test_dir}")
print(f"标签目标路径: {labels_test_dir}")

print(f"\n[剩余 train]")
print(f"剩余图片数量: {total_count - moved_val_img_count - moved_test_img_count}")