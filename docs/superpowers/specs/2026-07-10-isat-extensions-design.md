# ISAT 扩展包设计方案

**日期**: 2026-07-10
**仓库**: isat-yolo-lab (fork of yatengLG/ISAT_with_segment_anything)
**目标**: 在原 ISAT 源码不改动的前提下，新增两个独立扩展包，使 AI Agent (Claude Code 等) 能端到端操控标注流水线和 YOLO 训练流程。

---

## 1. 设计目标

1. **零修改**：`ISAT/` 目录下所有源文件一字不动
2. **AI 可发现**：两个包都提供 `capabilities` 命令输出机器可读的能力清单
3. **AI 可操作**：所有命令输出结构化 JSON，适配 Agent 解析
4. **无 GUI 依赖**：两个包都不 import PyQt5，纯 Python，可无头运行

---

## 2. 整体架构

```
isat-yolo-lab/
├── ISAT/                 # ★ 原仓库，完全不动
├── isat_agent_cli/       # ★ 插件1：AI 操控 ISAT 的 CLI（目录名用下划线，Python包规范）
│   ├── __init__.py
│   ├── cli.py            # click 主入口，注册为命令 `isat-agent`
│   └── commands/
│       ├── project.py    # 项目管理
│       ├── category.py   # 类别管理
│       ├── convert.py    # 格式互转
│       ├── stats.py      # 数据统计
│       ├── validate.py   # 标注校验
│       ├── batch.py      # 批量操作
│       ├── media.py      # 媒体处理
│       └── model.py      # SAM 模型管理
├── isat_yolo/            # ★ 插件2：YOLO 训练全流程（目录名用下划线，Python包规范）
│   ├── __init__.py
│   ├── cli.py            # click 主入口，注册为命令 `isat-yolo`
│   └── commands/
│       ├── dataset.py    # 数据准备
│       ├── train.py      # 训练执行
│       ├── eval.py       # 评估分析
│       ├── log.py        # 日志分析 & 调参建议
│       ├── predict.py    # 推理
│       └── config.py     # 配置管理
└── setup.py              # ★ 只追加 entry_points，不改原有配置
```

### 依赖关系

```
isat-agent-cli  ──imports──▶  ISAT.formats.*  (只读)
isat-yolo       ──imports──▶  ultralytics     (训练引擎)
isat-yolo       ──可选调用──▶ isat-agent-cli  (数据准备阶段)
```

---

## 3. isat-agent-cli 详细设计

### 3.1 命令树

```
isat-agent
├── project init       --images <dir> --categories <list> [--output <dir>]
├── project info       --project <dir>
├── project open       --project <dir>
├── category list      --project <dir>
├── category add       --project <dir> --name <str> [--color <hex>]
├── category remove    --project <dir> --name <str>
├── category rename    --project <dir> --old <str> --new <str>
├── category merge     --project <dir> --source <str> --target <str>
├── convert isat2yolo  --json-root <dir> --txt-root <dir> [--ignore-background]
├── convert yolo2isat  --images <dir> --txts <dir> --out <dir> [--category-file <f>]
├── convert isat2coco  --json-root <dir> --out <file>
├── convert coco2isat  --coco-json <file> --out <dir>
├── convert isat2labelme --json-root <dir> --out <dir>
├── convert labelme2isat --json-root <dir> --out <dir>
├── convert isat2voc   --json-root <dir> --out <dir> [--instance|--semantic] [--use-setting-color]
├── convert isat2voc-det --json-root <dir> --out <dir>
├── stats dataset      --project <dir>
├── stats per-image    --project <dir>
├── stats category     --project <dir>
├── validate all       --project <dir>
├── validate empty     --project <dir>
├── validate geometry  --project <dir>
├── validate category  --project <dir>
├── validate orphan    --project <dir>
├── batch modify-attrs --project <dir> --group <int> [--category <str>] [--iscrowd <bool>] ...
├── batch delete-by-cat --project <dir> --category <str>
├── batch reindex-group --project <dir>
├── media video2frames --video <file> --out <dir> [--fps <n>]
├── media exif-process --dir <dir>
├── media dicom-info   --file <dcm>
├── model list
├── model download     --name <str>
├── model remove       --name <str>
└── capabilities
```

### 3.2 关键命令行为

**project init**: 不复制图片（避免磁盘浪费），而是在输出目录创建 `isat.yaml` 类别文件和一个指向图片目录的配置，供 ISAT GUI 打开。

```json
{"ok": true, "data": {"project_dir": "/path/to/project", "images": 150, "categories": ["猫","狗","鸟"]}}
```

**project info**: 扫描项目目录下所有 ISAT json 标注文件，统计：图片总数、已标注数、类别数、多边形总数、分组数。

**convert**: 直接复用 `ISAT.formats.YOLO`, `ISAT.formats.COCO` 等类的转换方法，新增内容只有 CLI 参数解析和日志输出。

**validate**: 返回所有问题列表，每条标注定位到具体文件和行：
```json
{"ok": true, "data": {"issues": [
  {"file": "001.json", "severity": "error", "type": "empty", "detail": "标注对象数为0"},
  {"file": "002.json", "severity": "warning", "type": "orphan_txt", "detail": "标签文件002.txt存在但无对应图片"}
]}}
```

### 3.3 实现方式

- **CLI 框架**: `click`
- **数据层**: `from ISAT.formats import YOLO, COCO, LABELME, VOC, VOCDetect`（只读复用）
- **实现方式**: 所有的命令类都是去掉了 `QThread`/`pyqtSignal` 的纯 Python 版本，业务逻辑直接从 `converter_dialog.py` 等文件中迁移

---

## 4. isat-yolo 详细设计

### 4.1 命令树

```
isat-yolo
├── dataset init       --json-root <dir> --images <dir> --out <dir>
├── dataset split      --dataset <dir> [--mode random|every-nth] [--val-ratio 0.2] [--include-test] [--test-ratio 0.1]
├── dataset balance    --dataset <dir>
├── dataset yaml       --dataset <dir> [--names 猫,狗,鸟] [--path <root>]
├── train new          --data <yaml> --model <pt> [训练超参...]
├── train resume       --data <yaml> --last-pt <file>
├── train finetune     --data <yaml> --best-pt <file> [训练超参...]
├── eval val           --data <yaml> --best-pt <file> [--batch 16]
├── eval summary       --results-dir <dir>
├── eval per-class     --results-dir <dir> [--class <name>]
├── log history        --log-dir <dir>
├── log compare        --log-dir <dir> --exp1 <name> --exp2 <name>
├── log suggest        --log-dir <dir> [--exp <name>]
├── predict image      --model <pt> --source <file> [--conf 0.25] [--save-dir <dir>]
├── predict batch      --model <pt> --source <dir> [--conf 0.25]
├── predict video      --model <pt> --source <file> [--conf 0.25]
├── config show
├── config set         [--epochs <n>] [--imgsz <n>] [--batch <n>] [--device <str>] ...
└── capabilities
```

### 4.2 训练超参数

参考 YOLO-LAB-GUI 的 `core/config.py:TrainConfig` dataclass：

| 参数 | 默认值 | 说明 |
|------|--------|------|
| `--epochs` | 150 | 训练轮数 |
| `--imgsz` | 640 | 输入尺寸 |
| `--batch` | 16 | 批大小 |
| `--device` | 自动检测 | cuda / cpu / mps |
| `--lr0` | 0.0005 | 初始学习率 |
| `--close-mosaic` | 10 | 最后 N 轮关闭 mosaic |
| `--multi-scale` | 0.5 | 多尺度训练概率 |
| `--augment / --no-augment` | true | 数据增强开关 |

数据增强参数（`--augment` 时生效）：

| 参数 | 默认值 |
|------|--------|
| `--hsv-h` | 0.015 |
| `--hsv-s` | 0.7 |
| `--hsv-v` | 0.4 |
| `--degrees` | 0.0 |
| `--translate` | 0.1 |
| `--scale` | 0.5 |
| `--shear` | 0.0 |
| `--perspective` | 0.0 |
| `--flipud` | 0.0 |
| `--fliplr` | 0.5 |
| `--mosaic` | 1.0 |
| `--mixup` | 0.0 |
| `--copy-paste` | 0.0 |

### 4.3 配置管理

优先级：**默认值 → `~/.yolo-lab/config.yaml` → CLI 参数**

- `config show` 输出当前生效的完整配置
- `config set --epochs 200` 写入 `~/.yolo-lab/config.yaml`，后续训练自动继承
- 这一机制与 YOLO-LAB-GUI 共享同一配置文件，GUI 和 CLI 可互操作

### 4.4 训练日志 & AI 决策支持

**日志文件**（标准路径：`<results_dir>/<experiment_name>/`）：
- `train_log.csv`：训练事件日志（开始/结束/失败）
- `result_summary_log.csv`：整体评估指标
- `result_per_class_log.csv`：逐类别评估指标

**log suggest 命令** — AI 决策的核心能力，分析训练结果给出建议：

```json
{
  "ok": true,
  "data": {
    "experiment": "exp_20260710",
    "metrics": {"mAP50": 0.72, "mAP50-95": 0.45},
    "analysis": {
      "overfitting": {"detected": false, "detail": "train/val loss gap正常"},
      "underfitting": {"detected": true, "detail": "mAP仍在上升但epochs已用完", "suggestion": "建议增加epochs至200-250"},
      "learning_rate": {"status": "ok", "detail": "loss曲线平滑下降"},
      "class_balance": [
        {"class": "鸟", "instances": 30, "mAP50": 0.45, "status": "few", "suggestion": "数据量少且性能低，建议收集更多数据或启用更强增强"}
      ]
    },
    "suggestions": [
      "增加epochs到200以上",
      "鸟类数据偏少(30张)，考虑收集更多样本或增加copy_paste增强"
    ]
  }
}
```

### 4.5 实现方式

- **CLI 框架**: `click`
- **训练引擎**: `ultralytics.YOLO`
- **配置类**: 复用 YOLO-LAB-GUI 的 `TrainConfig` dataclass 设计，内联实现避免跨仓库依赖
- **日志系统**: 复用 `train_logger.py` 的 CSV 格式设计
- **工具脚本**: 复用 YOLO-LAB-GUI `tools/dataset_tools/` 的拆分逻辑

---

## 5. AI 发现机制

两个包各自提供 `capabilities` 命令，输出完整能力清单 JSON：

```bash
$ isat-agent capabilities
```

```json
{
  "package": "isat-agent-cli",
  "version": "0.1.0",
  "description": "CLI interface for ISAT annotation tool",
  "commands": [
    {
      "name": "project",
      "description": "项目管理：创建、打开、查看ISAT项目",
      "subcommands": [
        {"name": "init", "description": "创建新项目", "args": ["--images", "--categories", "--output"]},
        {"name": "info", "description": "查看项目状态", "args": ["--project"]},
        {"name": "open", "description": "验证并打开已有项目", "args": ["--project"]}
      ]
    }
  ]
}
```

同样的 `isat-yolo capabilities` 输出 YOLO 训练能力清单。

AI Agent 使用流程：
1. `which isat-agent` 确认已安装
2. `isat-agent capabilities` 获取能力全貌
3. 根据用户意图，选择对应命令执行
4. 解析 JSON 输出，决策下一步操作

---

## 6. 安装方式

`setup.py` 追加新的 entry_points（不改原有配置）：

```python
entry_points={
    "console_scripts": [
        "isat-sam=ISAT.main:main",           # 原有，不动
        "isat-agent=isat_agent_cli.cli:main", # 新增
        "isat-yolo=isat_yolo.cli:main",      # 新增
    ],
    "isat.plugins": [],                       # 原有，不动
},
```

两个扩展包不单独发布 PyPI，随 `isat-yolo-lab` 仓库一起 `pip install -e .` 安装。

---

## 7. 约束 & 不做什么

1. **不改动 `ISAT/` 下任何文件**（除非是 bug fix 向上游提 PR）
2. 不实现 Web UI 或 API server（后续可加）
3. `isat-yolo` 只做 YOLO 分割/检测训练，不做 SAM 微调（SAM 模型管理在 `isat-agent-cli` 侧）
4. 不在两个包之间硬编码依赖
5. 训练进度监控依赖 ultralytics 原生日志输出，不加实时推送

---

## 8. 成功标准

1. `isat-agent capabilities` 返回完整 JSON，AI Agent 可据此自主发现所有可用命令
2. `isat-agent project init --images ./photos --categories 猫,狗` 创建可用项目，ISAT GUI 打开即可标注
3. `isat-agent convert isat2yolo` 成功将标注转换为 YOLO 格式
4. `isat-yolo dataset init + split + yaml` 一键准备好可训练数据集
5. `isat-yolo train new` + `log suggest` 完成训练 & AI 决策闭环
