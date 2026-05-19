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

    train_dir = str(base / "images" / "train")
    val_dir = str(base / "images" / "val")

    os.makedirs(val_dir, exist_ok=True)

    valid_ext = (".jpg", ".jpeg", ".png")

    images = [f for f in os.listdir(train_dir) if f.lower().endswith(valid_ext)]
    images.sort(key=lambda x: int(os.path.splitext(x)[0]))

    total_count = len(images)
    val_count = round(total_count * val_ratio)

    if val_count < 1:
        raise ValueError(f"按照当前比例 {val_ratio} 计算，验证集数量小于 1，请调大比例。")
    if val_count >= total_count:
        raise ValueError(f"按照当前比例 {val_ratio} 计算，验证集数量达到或超过训练集总数，请调小比例。")

    random.seed(42)
    val_images = random.sample(images, val_count)

    for img in val_images:
        src = os.path.join(train_dir, img)
        dst = os.path.join(val_dir, img)
        shutil.move(src, dst)

    print(f"原训练集图片总数: {total_count}")
    print(f"设置比例: {val_ratio * 100:.1f}%")
    print(f"移动到 val 的图片数量: {val_count}")
    print(f"已完成，图片已移动到: {val_dir}")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="随机分割数据集为 train/val（仅图片）")
    p.add_argument("--dataset-dir", default=None, help="数据集根目录（默认自动检测）")
    p.add_argument("--val-ratio", type=float, default=0.20, help="验证集比例 (默认 0.20)")
    args = p.parse_args()
    run(dataset_dir=args.dataset_dir, val_ratio=args.val_ratio)
