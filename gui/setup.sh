#!/usr/bin/env bash
# ── YOLO Lab GUI 一键环境搭建 ──
# 用法: git clone <url> && cd yolo_lab_gui && bash setup.sh
set -euo pipefail

echo "=== YOLO Lab GUI 环境搭建 ==="

# 1. 检查 conda
if ! command -v conda &>/dev/null; then
    echo "[错误] 请先安装 Miniconda: https://docs.conda.io/en/latest/miniconda.html"
    exit 1
fi

# 2. 创建 conda 环境（如已存在则跳过）
ENV_NAME="${1:-yolo}"
if conda env list | grep -q "^${ENV_NAME} "; then
    echo "[跳过] conda 环境 '${ENV_NAME}' 已存在"
else
    echo "[创建] conda 环境 '${ENV_NAME}'..."
    conda env create -f environment.yml
fi

# 3. 激活并安装依赖
echo "[安装] Python 依赖..."
conda run -n "$ENV_NAME" pip install -r requirements.txt

# 4. 创建必要目录
mkdir -p outputs/results outputs/logs outputs/predict

echo ""
echo "=== 搭建完成 ==="
echo "启动 GUI:"
echo "  conda activate ${ENV_NAME}"
echo "  python gui/main.py"
echo ""
echo "首次运行训练时，YOLO 基础模型 (yolov8n-seg.pt) 会自动下载。"
echo "如有本地权重文件，放到 pretrained_models/ 目录即可。"
