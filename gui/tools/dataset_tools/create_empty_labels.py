import os
from pathlib import Path

# 默认与仓库 data.yaml（path: data/dataset）下 YOLO 布局一致；可改为任意图片/标签目录
_REPO_ROOT = Path(__file__).resolve().parents[2]
image_dir = str(_REPO_ROOT / "data" / "dataset" / "images" / "train")
label_dir = str(_REPO_ROOT / "data" / "dataset" / "labels" / "train")

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