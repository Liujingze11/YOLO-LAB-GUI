# YOLO 图像分割训练工作室（中文）

一个基于 Ultralytics YOLO 的图像分割训练小项目。仓库把训练流程、配置管理、日志记录与验证分离，便于复现实验并做对比分析。

---

## 快速概览

- 目标：提供可复现、可管理的分割训练工作流（支持新训练、断点续训和基于历史 best.pt 的微调）。
- 语言：Python 3.8+
- 依赖：ultralytics、pyyaml（安装见下）

---

## 主要功能

- 三种训练模式：新训练 / 继续上次训练 / 基于历史 best.pt 继续训练
- 训练前确认（打印关键参数以避免误操作）
- 可开关的数据增强（集中配置）
- 自动验证并写入 CSV 日志（整体验证与按类日志）
- 实验隔离：每次训练生成独立结果目录和日志，便于对比

---

## 项目结构（简化）

```text
code/
├── dataset_tools/         # 数据划分与标签工具
│   ├── create_empty_labels.py
│   ├── split_images_only/
│   │   ├── split_every_5th_images_only.py
│   │   └── split_random_images_only.py
│   ├── split_train_val/
│   │   ├── split_every_5th_with_labels.py
│   │   └── split_random_with_labels.py
│   └── split_train_val_test/
│       └── split_random_with_labels.py
├── pretrained_models/     # 常用预训练权重（如 yolov8n.pt, yolov8n-seg.pt）
├── result/                # 每次训练的结果目录
├── scripts/               # 训练、配置与日志脚本
│   ├── config.py
│   ├── paths.py
│   ├── train_logger.py
│   ├── train_segment.py
│   └── predict_test.py
├── train_logs/            # CSV 日志：train_log / result_summary / result_per_class
├── data.yaml              # 数据集配置（类别、train/val 路径）
├── data/                  # 原始与准备好的数据集（json_space, Source Data, datasets*）
├── predict/               # 推理输出图像（overlay 示例）
└── isat-sam/              # onnx 模型、类名等相关文件
```

---

## 环境与安装

推荐使用虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install ultralytics pyyaml
```

如果你使用 conda，可以创建并激活一个 conda 环境：

```bash
conda create -n yolo python=3.8 -y
conda activate yolo
pip install -U pip
pip install ultralytics pyyaml
```

提示：训练脚本（`scripts/train_segment.py`）现在支持命令行参数（通过 `argparse`）在运行时覆盖部分配置项。常用参数包括 `--epochs`、`--imgsz`、`--batch`、`--device` 和 `--name`。示例：

```bash
python scripts/train_segment.py --epochs 200 --imgsz 1280 --batch 8 --device 0,1 --name my_experiment
```

脚本仍会提示选择训练模式（1/2/3），并在开始前要求确认；数据增强的询问逻辑保持不变。

如需 GPU，请确保已安装匹配的 CUDA 驱动与 PyTorch（Ultralytics 使用系统 PyTorch）。

---

## 配置说明

### 路径自动检测

默认路径定义在 `scripts/paths.py` 中，并**自动基于项目根目录计算**——如果你的数据集结构符合项目标准布局，无需手动修改任何路径。只有当你的数据集或模型存放在非标准位置时才需要修改。

### TrainConfig（`scripts/config.py`）

训练超参与实验配置：

- 路径：`data_yaml`, `model_file`, `results_dir`, `log_dir`（默认值从 `paths.py` 导入，自动基于项目根目录检测）
- 超参：`epochs`, `imgsz`, `batch`, `device`
- 实验：`experiment_name`（用于生成 `save_dir`）
- 增强：`use_augment` 及 `hsv_h/hsv_s/hsv_v/translate/scale/mosaic/mixup/copy_paste` 等
- 自动属性：`save_dir`, `last_pt`, `best_pt`（通过 property 计算）

提示：超参也可以在运行时通过命令行参数覆盖（参见”命令行参数与非交互式用法”一节），例如 `--epochs`、`--imgsz`、`--batch`、`--device` 和 `--name`。

---

## 快速开始

1. 编辑 `data.yaml`：将 `path` 设置为你的数据集目录，并按实际类别修改 `names`。
2. （可选）如果你的数据或模型不在标准位置，编辑 `scripts/paths.py`。
3. 启动训练：

```bash
python scripts/train_segment.py
```

脚本会提示选择训练模式：

- 输入 `1`：开启新训练（使用 `config.model_file` 作为起点）
- 输入 `2`：继续上次训练（需在当前实验文件夹存在 `last.pt`）
- 输入 `3`：从历史 `best.pt` 继续（扫描 `results_dir` 并选择实验）

训练开始前，会打印关键参数并在未固定增强配置时询问是否启用数据增强。

---

## 日志与验证

项目会把三类 CSV 日志写入 `train_logs/`：

- `train_log.csv`：训练流程记录（时间、模式、状态、路径、超参、保存位置等）
- `result_summary_log.csv`：整体验证指标（图片/实例数、box/mask mAP、precision/recall）
- `result_per_class_log.csv`：每类指标与样本分布（用于定位弱类）

训练结束后会自动运行验证并写入日志；日志还包含验证集中按类的图片数与实例数。

---

## 推荐流程

1. 准备数据集和 `data.yaml`（如需划分数据集，可使用 `dataset_tools/`）。
2. 在 `scripts/config.py` 中设置新的 `experiment_name`（避免覆盖）。
3. 运行 `python scripts/train_segment.py` 并选择合适模式。
4. 训练结束后在 `result/<experiment_name>/weights/` 查看 `best.pt`、`last.pt`，并检查 `train_logs/` 中的对应条目。

---

## 常见问题与小贴士

- 要从特定历史模型微调，使用模式 3 并选择该实验的 `best.pt`。
- 若选择模式 2 时缺少 `last.pt`，脚本会提示并允许改为新训练。
- 若显存不足，可减小 `batch` 或 `imgsz`，或切换到 CPU（`device='cpu'`，较慢但可运行）。
- 建议把关键超参（epochs/imgsz/batch）写入 `experiment_name` 或保存到实验目录，便于复现实验。

---

## dataset_tools 说明

`dataset_tools/` 提供数据准备与划分工具，便于将图片与标签组织到 train/val/test：

主要脚本：

- `dataset_tools/create_empty_labels.py` — 为无标注图片生成空的 YOLO 标签文件（占位或伪标签用途）。
- `dataset_tools/split_images_only/` — 仅划分图片：
  - `split_every_5th_images_only.py`：每隔 N 张抽样（周期性抽样）。
  - `split_random_images_only.py`：随机抽取指定比例。
- `dataset_tools/split_train_val/` — 同时划分图片与标签：
  - `split_every_5th_with_labels.py`：按间隔划分并移动对应标签。
  - `split_random_with_labels.py`：随机划分并保证图片/标签配对。
- `dataset_tools/split_train_val_test/` — 支持三分（train/val/test），适用于需要独立测试集的场景。

使用建议：备份原数据或先在副本上测试；脚本一般接受源目录/目标目录及比例/间隔参数，详见脚本顶部注释；划分后请确认 `data.yaml` 中的路径正确；若标签格式非 YOLO，请先转换。

---

## 后续改进建议

- 增加统一推理脚本与导出支持（ONNX / TensorRT）
- 增加可视化工具（训练曲线、混淆矩阵、按类对比）
- 将训练参数自动保存为 JSON/TXT 到实验目录
- 增加测试集评估与 CI 检查

---

## 贡献与维护

欢迎提交 PR 或 issue：
- 完善验证脚本
- 增加对不同 Ultralytics 版本的兼容说明

---

最后提示：完成大改动后请更新 `experiment_name` 并保留旧实验以便回溯对比。

## 命令行参数与非交互式用法

训练脚本支持若干命令行参数（通过 `argparse`）以在运行时覆盖配置项：`--epochs`、`--imgsz`、`--batch`、`--device` 和 `--name`（实验名称）。`--device` 接受 GPU 设备描述字符串，例如 `"0"`、`"0,1"` 或 `"cpu"`。

示例（交互式模式，脚本仍会显示提示）：

```bash
python scripts/train_segment.py --epochs 200 --imgsz 1280 --batch 8 --device 0,1 --name my_experiment
```

若需尽量减少交互，请传入所需的参数并准备在提示时输入训练模式。若要实现完全自动化（CI/脚本），可在外部脚本中传入模式选择与确认输入。

## data.yaml 示例

一个最小的分割数据集 `data.yaml` 应包含数据路径与类别名称。示例：

```yaml
path: ./data/Source Data/datasets_all_pro   # 数据集的绝对或相对路径
train: images/train
val: images/val
names:
  0: class_a
  1: class_b
  2: class_c
```

请确认 `train` 和 `val` 路径与数据布局一致（可以是绝对路径或相对于 `path` 的相对路径）。

## 输出与日志保存位置

- 每次实验结果：`result/<experiment_name>/`（自动在项目根目录下创建）
- 检查点：`result/<experiment_name>/weights/last.pt` 和 `best.pt`
- CSV 日志：`train_logs/`（自动创建）包含 `train_log.csv`、`result_summary_log.csv` 和 `result_per_class_log.csv`
