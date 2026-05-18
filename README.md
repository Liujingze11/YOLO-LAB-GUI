# YOLO Lab GUI

桌面端 YOLO 分割模型训练 / 推理工具，Apple 风格简约界面。

## 快速开始

```bash
git clone https://github.com/Liujingze11/YOLO-LAB-GUI.git
cd yolo_lab_gui
bash setup.sh             # 一键搭建 conda 环境
conda activate yolo
python gui/main.py        # 启动 GUI
```

首次训练时，YOLO 基础模型 (`yolov8n-seg.pt`) 会自动下载。

## 依赖

- Python 3.10+
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- ultralytics, PySide6, PyYAML

手动安装：

```bash
conda create -n yolo python=3.10 -y
conda activate yolo
pip install -r requirements.txt
```

## 项目结构

```
yolo_lab_gui/
├── gui/                        # 桌面界面 (PySide6)
│   ├── main.py                 # 主窗口 + 程序入口
│   ├── styles.py               # 颜色 & 样式常量
│   ├── widgets.py              # 控件工厂函数
│   ├── workers.py              # 后台训练/推理线程
│   ├── config.py               # TrainConfig 训练配置数据类
│   ├── paths.py                # 路径定义
│   ├── train_engine.py         # 训练编排（3 种模式）
│   ├── train_logger.py         # CSV 日志
│   ├── infer_engine.py         # 推理引擎
│   ├── infer_task_params.json  # 推理任务参数
│   └── presets.json            # 用户预设（运行时生成）
├── tools/dataset_tools/        # 数据集分割 & 标签工具
├── data.yaml                   # 数据集配置
├── setup.sh                    # 一键环境搭建
├── environment.yml             # conda 环境定义
└── requirements.txt
```

## 使用说明

### 训练

1. 切换到「训练」页签
2. 设置 `data.yaml`、超参数和训练模式
3. 点击「开始训练」

支持三种模式：
- **新训练** — 从初始权重开始
- **续训** — 从上次中断的 `last.pt` 继续
- **微调** — 基于历史实验的 `best.pt`

### 推理

1. 切换到「推理」页签
2. 选择模型、输入源和输出目录
3. 点击「开始推理」

### 预设

训练页支持保存 / 加载配置预设，方便在不同实验间快速切换。预设保存在 `gui/presets.json`。

## 输出与日志

- 训练结果：`outputs/results/<experiment_name>/weights/` (best.pt, last.pt)
- 推理结果：`outputs/predict/`
- CSV 日志：`outputs/logs/` (train_log, result_summary, result_per_class)

## data.yaml 格式

```yaml
path: data/datasets
train: images/train
val: images/val
names:
  0:
  1: milk
  2: crisp
  ...
```

## License

MIT
