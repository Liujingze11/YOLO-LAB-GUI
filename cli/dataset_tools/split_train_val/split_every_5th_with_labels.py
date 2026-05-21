import os
import shutil

# ===== 参数与路径配置 =====
images_train_dir = "请输入你的训练集地址"    # 图片训练集地址
images_val_dir = "请输入你的验证集目标地址"    # 图片测试集/验证集目标地址
labels_train_dir = "请输入你的训练集地址"    # 图片训练集地址
labels_val_dir = "请输入你的验证集目标地址"    # 图片测试集/验证集目标地址
times = 5

# 创建目标文件夹
os.makedirs(images_val_dir, exist_ok=True)
os.makedirs(labels_val_dir, exist_ok=True)

# 读取 train 中的图片
images = [f for f in os.listdir(images_train_dir) if f.lower().endswith(".jpg")]
images.sort(key=lambda x: int(os.path.splitext(x)[0]))

# ===== 照片与标签移动 =====
moved_img_count = 0
moved_label_count = 0
missing_label_count = 0

for img in images:
    name_without_ext = os.path.splitext(img)[0]

    # 只处理文件名是纯数字的图片，例如 1.jpg, 25.jpg
    if not name_without_ext.isdigit():
        print(f"跳过非纯数字文件名图片: {img}")
        continue

    num = int(name_without_ext)

    if num % times == 0:
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

print(f"图片移动完成：{moved_img_count} 个")
print(f"标签移动完成：{moved_label_count} 个")
print(f"缺失标签数量：{missing_label_count} 个")