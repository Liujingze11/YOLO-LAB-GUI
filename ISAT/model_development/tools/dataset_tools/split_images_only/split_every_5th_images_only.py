import os
import shutil
from pathlib import Path


def run(dataset_dir=None, interval=5):
    if dataset_dir:
        base = Path(dataset_dir)
    else:
        _REPO_ROOT = Path(__file__).resolve().parents[3]
        base = _REPO_ROOT / "data" / "dataset"

    train_dir = str(base / "images" / "train")
    val_dir = str(base / "images" / "val")

    os.makedirs(val_dir, exist_ok=True)

    images = [f for f in os.listdir(train_dir) if f.lower().endswith(".jpg")]
    images.sort(key=lambda x: int(os.path.splitext(x)[0]))

    for img in images:
        num = int(os.path.splitext(img)[0])
        if num % interval == 0:
            src = os.path.join(train_dir, img)
            dst = os.path.join(val_dir, img)
            shutil.move(src, dst)

    print(f"已将 {interval} 的倍数编号图片移动到 val")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="每 N 张分割数据集为 train/val（仅图片）")
    p.add_argument("--dataset-dir", default=None, help="数据集根目录（默认自动检测）")
    p.add_argument("--interval", type=int, default=5, help="间隔 N (默认 5，即每 5 张取 1 张到 val)")
    args = p.parse_args()
    run(dataset_dir=args.dataset_dir, interval=args.interval)
