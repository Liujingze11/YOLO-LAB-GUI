import os
import random
import shutil
from pathlib import Path


def run(dataset_dir=None, val_ratio=0.20):
    if dataset_dir:
        base = Path(dataset_dir)
    else:
        _REPO_ROOT = Path(__file__).resolve().parents[3]
        base = _REPO_ROOT / "data" / "dataset"

    images_train_dir = str(base / "images" / "train")
    images_val_dir = str(base / "images" / "val")
    labels_train_dir = str(base / "labels" / "train")
    labels_val_dir = str(base / "labels" / "val")

    os.makedirs(images_val_dir, exist_ok=True)
    os.makedirs(labels_val_dir, exist_ok=True)

    valid_ext = (".jpg", ".jpeg", ".png")

    images = [f for f in os.listdir(images_train_dir) if f.lower().endswith(valid_ext)]

    valid_images = []
    for f in images:
        name_without_ext = os.path.splitext(f)[0]
        if name_without_ext.isdigit():
            valid_images.append(f)
        else:
            print(f"跳过非纯数字文件名图片: {f}")

    valid_images.sort(key=lambda x: int(os.path.splitext(x)[0]))

    total_count = len(valid_images)
    val_count = round(total_count * val_ratio)

    if val_count < 1:
        raise ValueError(f"按照当前比例 {val_ratio} 计算，验证集数量小于 1，请调大比例。")
    if val_count >= total_count:
        raise ValueError(f"按照当前比例 {val_ratio} 计算，验证集数量达到或超过训练集总数，请调小比例。")

    random.seed(42)
    val_images = random.sample(valid_images, val_count)

    moved_img_count = 0
    moved_label_count = 0
    missing_label_count = 0

    for img in val_images:
        name_without_ext = os.path.splitext(img)[0]

        img_src = os.path.join(images_train_dir, img)
        img_dst = os.path.join(images_val_dir, img)
        shutil.move(img_src, img_dst)
        moved_img_count += 1

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


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="随机分割数据集为 train/val（含标签）")
    p.add_argument("--dataset-dir", default=None, help="数据集根目录（默认自动检测）")
    p.add_argument("--val-ratio", type=float, default=0.20, help="验证集比例 (默认 0.20)")
    args = p.parse_args()
    run(dataset_dir=args.dataset_dir, val_ratio=args.val_ratio)
