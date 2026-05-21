import os
import random
import shutil

# ===== 参数与路径配置 =====
images_train_dir = "请输入你的训练集地址"    # 图片训练集地址
images_val_dir = "请输入你的验证集目标地址"    # 图片测试集/验证集目标地址
labels_train_dir = "请输入你的训练集地址"    # 图片训练集地址
labels_val_dir = "请输入你的验证集目标地址"    # 图片测试集/验证集目标地址
val_ratio = 0.20   # 比例，例如 20% 就写 0.20

# 创建目标文件夹
os.makedirs(images_val_dir, exist_ok=True)
os.makedirs(labels_val_dir, exist_ok=True)

# 支持的图片格式
valid_ext = (".jpg", ".jpeg", ".png")

# 读取训练集图片
images = [f for f in os.listdir(images_train_dir) if f.lower().endswith(valid_ext)]

# 只保留“文件名去掉后缀后是纯数字”的图片，避免排序时报错
valid_images = []
for f in images:
    name_without_ext = os.path.splitext(f)[0]
    if name_without_ext.isdigit():
        valid_images.append(f)
    else:
        print(f"跳过非纯数字文件名图片: {f}")

# 按数字排序
valid_images.sort(key=lambda x: int(os.path.splitext(x)[0]))

# 统计总数
total_count = len(valid_images)

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
val_images = random.sample(valid_images, val_count)

moved_img_count = 0
moved_label_count = 0
missing_label_count = 0

# 移动图片和对应标签
for img in val_images:
    name_without_ext = os.path.splitext(img)[0]

    # ---- 移动图片 ----
    img_src = os.path.join(images_train_dir, img)
    img_dst = os.path.join(images_val_dir, img)
    shutil.move(img_src, img_dst)
    moved_img_count += 1

    # ---- 移动对应标签 ----
    label_name = name_without_ext + ".txt"
    label_src = os.path.join(labels_train_dir, label_name)
    label_dst = os.path.join(labels_val_dir, label_name)

    if os.path.exists(label_src):
        shutil.move(label_src, label_dst)
        moved_label_count += 1
    else:
        print(f"警告：未找到对应标签文件 {label_src}")
        missing_label_count += 1

print(f"原训练集图片总数: {total_count}")
print(f"设置比例: {val_ratio * 100:.1f}%")
print(f"计划移动到 val 的图片数量: {val_count}")
print(f"实际移动图片数量: {moved_img_count}")
print(f"实际移动标签数量: {moved_label_count}")
print(f"缺失标签数量: {missing_label_count}")
print(f"已完成，图片已移动到: {images_val_dir}")
print(f"已完成，标签已移动到: {labels_val_dir}")