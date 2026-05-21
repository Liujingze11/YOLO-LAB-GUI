import os

image_dir = "图片"
label_dir = "标签"

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