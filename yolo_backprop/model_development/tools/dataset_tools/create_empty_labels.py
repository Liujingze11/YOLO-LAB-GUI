import os
from pathlib import Path


def run(dataset_dir=None):
    if dataset_dir:
        base = Path(dataset_dir)
    else:
        _REPO_ROOT = Path(__file__).resolve().parents[2]
        base = _REPO_ROOT / "data" / "dataset"

    image_dir = str(base / "images" / "train")
    label_dir = str(base / "labels" / "train")

    os.makedirs(label_dir, exist_ok=True)

    image_exts = {".jpg", ".jpeg", ".png", ".bmp", ".webp"}

    for filename in os.listdir(image_dir):
        name, ext = os.path.splitext(filename)
        if ext.lower() in image_exts:
            label_path = os.path.join(label_dir, f"{name}.txt")
            if not os.path.exists(label_path):
                with open(label_path, "w", encoding="utf-8") as f:
                    pass

    print("已根据图片文件名生成对应的空标签文件")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="为无标签图片生成空 .txt 标注文件")
    p.add_argument("--dataset-dir", default=None, help="数据集根目录（默认自动检测）")
    args = p.parse_args()
    run(dataset_dir=args.dataset_dir)
