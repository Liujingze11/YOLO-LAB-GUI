import os
import shutil

# ===== 参数与路径配置 =====
train_dir = "请输入你的训练集地址"  # 训练集文件夹路径（源目录），包含所有图片
val_dir = "请输入你的验证集目标地址"    # 验证集文件夹路径（目标目录），用于存放挑选出的图
times = 5   # 倍数

# 创建目标文件夹
os.makedirs(val_dir, exist_ok=True) 

# 读取训练集图片
images = [f for f in os.listdir(train_dir) if f.lower().endswith(".jpg")]
images.sort(key=lambda x: int(os.path.splitext(x)[0]))

# ===== 照片移动 =====
for img in images:
    num = int(os.path.splitext(img)[0])
    if num % times == 0:
        src = os.path.join(train_dir, img)
        dst = os.path.join(val_dir, img)
        shutil.move(src, dst)

print("已将 5 的倍数编号图片移动到 val")