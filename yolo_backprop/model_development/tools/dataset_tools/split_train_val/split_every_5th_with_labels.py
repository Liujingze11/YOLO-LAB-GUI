import os
import shutil
from pathlib import Path


def run(dataset_dir=None, interval=5):
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

    images = [f for f in os.listdir(images_train_dir) if f.lower().endswith(".jpg")]
    images.sort(key=lambda x: int(os.path.splitext(x)[0]))

    moved_img_count = 0
    moved_label_count = 0
    missing_label_count = 0

    for img in images:
        name_without_ext = os.path.splitext(img)[0]

        if not name_without_ext.isdigit():
            print(f"跳过非纯数字文件名图片: {img}")
            continue

        num = int(name_without_ext)

        if num % interval == 0:
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

    print(f"图片移动完成：{moved_img_count} 个")
    print(f"标签移动完成：{moved_label_count} 个")
    print(f"缺失标签数量：{missing_label_count} 个")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="每 N 张分割数据集为 train/val（含标签）")
    p.add_argument("--dataset-dir", default=None, help="数据集根目录（默认自动检测）")
    p.add_argument("--interval", type=int, default=5, help="间隔 N (默认 5，即每 5 张取 1 张到 val)")
    args = p.parse_args()
    run(dataset_dir=args.dataset_dir, interval=args.interval)
