# YOLO Lab GUI

[English](README.md) | [Français](README_fr.md) | [Español](README_es.md)

桌面端 YOLO 分割模型训练/推理工具，Apple 风格简约界面。

## 功能

- **训练** — 新训练/续训/微调三种模式，支持数据增强、预设管理
- **推理** — 图像分割推理，可视化进度条
- **工具** — 数据集分割、空标签创建等常用工具
- **日志 & 结果** — 历史训练日志查看、实验结果浏览
- 初始权重自动下载（下拉框选择）
- 暗色/亮色模式切换
- 中/英/法/西班牙 四语言切换（GUI + 终端输出）
- 训练/推理在子进程中运行，可随时停止

## 快速开始

```bash
git clone https://github.com/Liujingze11/YOLO-LAB-GUI.git
cd YOLO-LAB-GUI
bash setup.sh
conda activate yolo
python gui/main.py
```

## 依赖

- Python 3.10+
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- ultralytics >= 8.0.0, PySide6 >= 6.5.0, PyYAML >= 6

手动安装：

```bash
conda create -n yolo python=3.10 -y
conda activate yolo
pip install -r requirements.txt
```

## 项目结构

```
YOLO-LAB-GUI/
├── gui/                    # 桌面界面 (PySide6)
│   ├── main.py             # 主窗口 + 程序入口
│   ├── styles.py           # 颜色 & 样式常量（含亮/暗主题）
│   ├── widgets.py          # 控件工厂函数
│   ├── model_selector.py   # 模型选择器（含自动下载弹窗）
│   ├── i18n.py             # 多语言翻译管理器
│   ├── workers.py          # 后台训练/推理线程
│   ├── config.py           # TrainConfig 训练配置数据类
│   ├── device.py           # 设备自动检测
│   ├── paths.py            # 路径定义
│   ├── train_engine.py     # 训练编排（3 种模式）
│   ├── train_logger.py     # CSV 日志
│   └── infer_engine.py     # 推理引擎
├── locales/                # 翻译文件 (zh/en/fr/es)
├── tools/dataset_tools/    # 数据集分割 & 标签工具
├── pretrained_models/      # 预训练模型缓存
├── data.yaml               # 数据集配置
├── setup.sh                # 一键环境搭建
├── environment.yml         # conda 环境定义
└── requirements.txt
```

## 使用说明

### 训练

1. 切换到「训练」页签
2. 设置 `data.yaml`、超参数和训练模式
3. 点击「开始训练」

支持三种模式：
- **新训练** — 从初始权重开始
- **续训** — 从上一次中断的 `last.pt` 继续
- **微调** — 基于历史实验的 `best.pt`

### 推理

1. 切换到「推理」页签
2. 选择模型、输入源和输出目录
3. 点击「开始推理」

### 语言切换

右上角下拉框切换中文/English/Français/Español，界面文字和训练/推理终端输出均会同步切换。

## 输出与日志

- 训练结果：`outputs/results/<experiment_name>/weights/` (best.pt, last.pt)
- 推理结果：`outputs/predict/`
- CSV 日志：`outputs/logs/`

## data.yaml 格式

```yaml
path: data/datasets
train: images/train
val: images/val
names:
  0: class_a
  1: class_b
```

## License

MIT
