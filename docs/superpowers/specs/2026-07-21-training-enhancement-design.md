# YOLO-LAB-GUI 训练增强 & 数据转换 设计文档

**日期**: 2026-07-21
**状态**: 已确认
**范围**: YOLO-LAB-GUI 桌面应用

---

## 1. 目标

在现有 YOLO-LAB-GUI 应用基础上，新增以下 4 项功能并完成架构重构：

| 序号 | 功能 | 说明 |
|------|------|------|
| F1 | 数据增强精细控制 | 在 GUI 中暴露全部 12 个增强参数 |
| F2 | 高级超参数面板 | 暴露学习率/优化器/正则化等约 15 个参数，可折叠 |
| F3 | 实时训练曲线 | matplotlib 嵌入式 loss/mAP 实时图表 |
| F4 | 模型导出（数据转换） | 新增标签页，支持 ONNX/TensorRT/OpenVINO/CoreML/TFLite 导出 |

---

## 2. 架构变更

### 2.1 文件拆分

当前 `main.py` 有 1542 行，所有标签页混在一个文件中。重构为：

```
main.py                          # 精简为 ~200 行（窗口骨架 + 标签页组装 + 信号连线）
gui/
├── tabs/                        # 🆕 标签页模块（每个标签页独立文件）
│   ├── __init__.py
│   ├── train_tab.py             # 训练页
│   ├── infer_tab.py             # 推理页
│   ├── export_tab.py            # 🆕 数据转换页
│   ├── logs_tab.py              # 日志 & 结果页
│   ├── tools_tab.py             # 工具页
│   └── settings_tab.py          # 设置页
├── charts/                      # 🆕 训练曲线模块
│   └── training_chart.py        # matplotlib FigureCanvas 嵌入式实时曲线
├── widgets.py                   # 📝 新增可折叠面板、导出格式卡片工厂函数
├── workers.py                   # 📝 新增 ExportWorker，TrainWorker 增强 metrics 解析
├── export_engine.py             # 🆕 模型导出子进程入口脚本
├── model_selector.py            # 不变
├── train_engine.py              # 不变
├── infer_engine.py              # 不变
├── styles.py                    # 📝 新增导出卡片、可折叠区域样式
├── i18n.py                      # 不变
└── paths.py                     # 不变

core/
├── config.py                    # 📝 TrainConfig 补充 optimizer/momentum/warmup 等字段
├── training.py                  # 📝 build_train_kwargs 补充所有高级超参数
├── export.py                    # 🆕 模型导出逻辑（格式检测、导出参数构建）
├── ...                          # 其余文件不变
```

### 2.2 模块职责

| 模块 | 职责 |
|------|------|
| `main.py` | 创建 QApplication，组装 6 个标签页，初始化主题/语言/快捷键，事件循环 |
| `gui/tabs/train_tab.py` | 训练页完整 UI + 信号处理，包含 5 个卡片面板、实时曲线、预设管理 |
| `gui/tabs/export_tab.py` | 数据转换页完整 UI + 信号处理，格式卡片选择、导出参数、启动导出 |
| `gui/charts/training_chart.py` | matplotlib FigureCanvas 封装，管理 loss/mAP 曲线，支持缩放/平移 |
| `gui/export_engine.py` | 子进程脚本，接收 CLI 参数，调用 `model.export()` |
| `core/export.py` | 纯逻辑：格式参数验证、`InferConfig`-like dataclass |

---

## 3. 功能设计

### 3.1 F1 + F2: 训练页面板重新规划

训练页从 4 个面板扩展为 **5 个可拖拽卡片面板**（垂直 QSplitter）：

| 面板 | 内容 | 最小高度 |
|------|------|----------|
| **路径** (Paths) | data.yaml、初始权重、结果目录、日志目录 | 180px |
| **超参数** (Hyperparams) | 基础（epochs/imgsz/batch/device/实验名）+ 可折叠高级区域 | 140px（折叠）/ 320px（展开）|
| **数据增强** (Augmentation) | 启用开关 + 3 列参数（颜色抖动/几何变换/混合策略）| 160px |
| **训练模式** (Mode) | 新建/恢复/微调单选按钮 + 历史实验选择 | 130px |
| **监控** (Monitor) | 按钮栏 + 进度条 + 曲线/日志左右分栏 | 200px |

#### 3.1.1 高级超参数（可折叠区域）

**学习率 & 优化器列**:
- `lr0` (初始学习率, 默认 0.0005)
- `lrf` (最终学习率因子, 默认 0.01)
- `optimizer` (优化器选择, QComboBox: AdamW/SGD/Adam/RMSProp)
- `momentum` (动量, 默认 0.937)
- `weight_decay` (权重衰减, 默认 5e-4)
- `cos_lr` (余弦退火, QCheckBox, 默认 True)

**正则化 & 策略列**:
- `close_mosaic` (关闭马赛克增强的 epoch, 默认 10)
- `multi_scale` (多尺度训练因子, 默认 0.5)
- `dropout` (分类头 dropout, 默认 0.0)
- `label_smoothing` (标签平滑, 默认 0.0)
- `warmup_epochs` (预热 epoch 数, 默认 3.0)
- `warmup_momentum` (预热起始动量, 默认 0.8)

展开/收起动画: `QPropertyAnimation` 驱动 `maximumHeight`, duration=250ms, easing=OutCubic。

#### 3.1.2 数据增强面板

顶部 `QCheckBox` 全局开关。关闭时整个参数区域置灰（opacity 0.4），所有控件 disabled。

3 列布局，对齐紧凑：

**颜色抖动**:
- `hsv_h` (0.015), `hsv_s` (0.7), `hsv_v` (0.4)

**几何变换**:
- `degrees` (0.0), `translate` (0.1), `scale` (0.5), `shear` (0.0)
- `perspective` (0.0), `flipud` (0.0), `fliplr` (0.5)

**混合策略**:
- `mosaic` (1.0), `mixup` (0.0), `copy_paste` (0.0)

### 3.2 F3: 实时训练曲线

#### 3.2.1 布局

监控面板底部使用水平 `QSplitter` 分为左右两栏：
- **左侧**: 训练曲线图（matplotlib FigureCanvas）
- **右侧**: 日志区域（现有 `QTextEdit`）

#### 3.2.2 图表组件 (`gui/charts/training_chart.py`)

- 使用 `matplotlib.backends.backend_qtagg.FigureCanvasQTAgg`
- 上下两个子图：Loss 曲线（上）+ mAP 曲线（下）
- Loss 曲线：`box_loss`, `seg_loss`, `cls_loss`, `dfl_loss`（共 4 条）
- mAP 曲线：`mAP50`, `mAP50-95`（共 2 条）
- 支持缩放（滚轮）、平移（拖拽）、重置（工具栏按钮）
- 图例可点击切换曲线显隐
- 深色背景 + 与主题一致的配色

#### 3.2.3 数据流

```
TrainWorker (子进程 stdout 解析)
  │
  ├── log_line(str)          → 日志窗口（全部行）
  ├── progress(int)          → 进度条（epoch 进度）
  └── metrics_update(dict)   → 曲线图添加数据点  🆕
        │
        └── TrainingChart.append_metrics(epoch, box_loss, seg_loss,
               cls_loss, dfl_loss, mAP50, mAP50_95)
              │
              └── canvas.draw_idle()  (节流至 500ms/次)
```

#### 3.2.4 指标解析

Ultralytics 训练 stdout 输出格式（每 epoch）：
```
      Epoch    GPU_mem   box_loss   seg_loss   cls_loss   dfl_loss  Instances       Size
    1/150       2.5G      1.234      1.567     0.891      1.012         12        640
```

`TrainWorker._on_line()` 增强：识别以数字开头的 epoch 行（`^\s*\d+/\d+`），按列提取数值，组装为 dict 发射 `metrics_update`。

Validation mAP 在验证阶段从 `all ...` 行或标准 Ultralytics 输出中解析。

### 3.3 F4: 数据转换页（新标签页）

#### 3.3.1 UI 布局

从上到下 5 个区块：

1. **源模型**: 路径选择 + 自动检测信息（任务类型、输入尺寸）
2. **导出格式**: 5 张可点击卡片：ONNX / TensorRT / OpenVINO / CoreML / TFLite
3. **导出选项**: 根据所选格式动态显示相关参数
4. **输出目录**: 路径选择
5. **操作**: 导出按钮 + 进度条 + 日志

#### 3.3.2 格式卡片

每张卡片显示：
- 格式名 + 图标 emoji
- 简短描述（"通用推理部署" / "NVIDIA GPU 最快推理" 等）
- 点击选中：蓝色边框 + 浅蓝半透明背景 + 右上角 ✓

当模型文件未加载时，所有卡片为禁用态。

#### 3.3.3 导出选项（按格式动态切换）

| 格式 | 选项 |
|------|------|
| ONNX | imgsz (spinner), opset (combo 9~19), 动态 batch (checkbox), 简化模型 (checkbox), NMS (checkbox) |
| TensorRT | imgsz (spinner), fp16 (checkbox), int8 (checkbox), workspace GB (spinner) |
| OpenVINO | imgsz (spinner), int8 (checkbox), 动态 batch (checkbox) |
| CoreML | imgsz (spinner), nms (checkbox) |
| TFLite | imgsz (spinner), int8 (checkbox), fp16 (checkbox) |

使用 `QStackedWidget` 切换不同格式的参数面板。

#### 3.3.4 导出执行

- `ExportWorker(QThread)` → 子进程 `export_engine.py`
- 子进程调用 `model.export(format=..., **kwargs)`
- 进度由文件大小监控或 Ultralytics stdout 输出驱动
- 完成后在日志中显示导出文件路径和大小

---

## 4. Apple 风格交互规范

| 场景 | 效果 |
|------|------|
| 卡片悬停 | 阴影 blur 从 24px 过渡到 32px, offset 从 1px 到 2px, duration=150ms |
| 按钮按下 | scale(0.97), QSS `:pressed` 颜色下沉 |
| 折叠展开 | QPropertyAnimation 驱动 maxHeight, 250ms OutCubic |
| 格式卡片选中 | `border: 2px solid #0071e3; background: rgba(0,113,227,0.08);` |
| 禁用区域 | `setEnabled(False)` → 整体 opacity 0.4（Qt 自动处理） |
| Tab 切换 | 保持现有 border-bottom 下划线样式 |
| 进度条 | 现有圆角蓝色不变 |
| 滚动条 | 现有 6px 细滚动条不变 |

---

## 5. 数据模型变更

### 5.1 TrainConfig 新增字段 (`core/config.py`)

```python
# 优化器 & 学习率
optimizer: str = "AdamW"        # SGD / Adam / AdamW / RMSProp
momentum: float = 0.937
weight_decay: float = 0.0005
lrf: float = 0.01               # 最终 lr 因子
cos_lr: bool = True             # 余弦退火
warmup_epochs: float = 3.0
warmup_momentum: float = 0.8

# 正则化
dropout: float = 0.0
label_smoothing: float = 0.0
```

### 5.2 build_train_kwargs 补充 (`core/training.py`)

新增 kwargs 键：`optimizer`, `momentum`, `weight_decay`, `lrf`, `cos_lr`, `warmup_epochs`, `warmup_momentum`, `dropout`, `label_smoothing`。

### 5.3 ExportConfig 新增 (`core/export.py`)

```python
@dataclass
class ExportConfig:
    model_path: str = ""
    format: str = "onnx"         # onnx / engine / openvino / coreml / tflite
    imgsz: int = 640
    output_dir: str = ""
    # ONNX
    opset: int = 12
    dynamic: bool = True
    simplify: bool = True
    nms: bool = False
    # TensorRT
    fp16: bool = False
    int8: bool = False
    workspace: float = 4.0       # GB
```

### 5.4 preset.json 兼容

现有预设文件 `gui/presets.json` 只保存 TrainConfig 中已有字段的子集。重构时确保：
- `_get_current_config_dict()` 序列化所有新字段
- `_apply_config_dict()` 反序列化时对缺失字段使用默认值（向后兼容）

---

## 6. 国际化

所有新增 UI 文本需添加到 4 个 locale 文件（`locales/zh.json`, `en.json`, `fr.json`, `es.json`）。

新增翻译键（预估 ~60 个）：

| 域 | 键前缀 | 数量 |
|------|------|------|
| 高级超参数 | `train.adv.*` | ~15 |
| 数据增强面板 | `train.aug.*` | ~15 |
| 训练曲线 | `train.chart.*` | ~8 |
| 数据转换页 | `export.*` | ~20 |
| 导出格式 | `export.format.*` | ~10 |

---

## 7. 测试要点

- [ ] 训练页 QSplitter 5 个面板可正常拖拽，默认比例合理
- [ ] 高级参数折叠/展开动画流畅，状态在切换标签页后保持
- [ ] 增强关闭时所有参数控件 disabled + 视觉置灰
- [ ] 实时曲线数据点随 epoch 增加正确更新
- [ ] 曲线缩放/平移/重置交互正常
- [ ] 导出格式卡片点击切换，参数面板跟随变化
- [ ] 5 种导出格式均可正常执行并生成输出文件
- [ ] 导出过程中取消可正确终止子进程
- [ ] 语言切换后所有新 UI 文本正确翻译
- [ ] 暗色/亮色主题切换后曲线图背景跟随
- [ ] 旧 preset.json 在新版本中正常加载（向后兼容）
- [ ] Ctrl+Enter 快捷键在训练页和推理页正常触发

---

## 8. 实施顺序

| 阶段 | 内容 | 预估变更 |
|------|------|----------|
| **Phase 1** | 拆分 main.py → gui/tabs/*.py（纯重构，不改变行为） | main.py ✂️, 6 个 tab 文件 🆕 |
| **Phase 2** | TrainConfig + build_train_kwargs 扩展（高级超参数字段） | core/config.py, core/training.py |
| **Phase 3** | 数据增强面板（训练页新增面板 + UI） | gui/tabs/train_tab.py |
| **Phase 4** | 高级超参数面板（可折叠区域 + UI） | gui/tabs/train_tab.py |
| **Phase 5** | 实时训练曲线（matplotlib 嵌入 + TrainWorker 增强） | gui/charts/*, gui/workers.py |
| **Phase 6** | 数据转换页（新标签页 + ExportWorker + export_engine） | gui/tabs/export_tab.py, gui/export_engine.py, core/export.py |
| **Phase 7** | i18n 翻译补充（4 种语言 × 60 键） | locales/*.json |
| **Phase 8** | 设置页扩展（可选）：默认路径、快捷键配置等 | gui/tabs/settings_tab.py |

---

## 9. 风险 & 缓解

| 风险 | 缓解 |
|------|------|
| matplotlib 嵌入 Qt 性能 | 节流 500ms 更新，`draw_idle()` 非强制重绘 |
| 子进程 metrics 解析不稳定 | 正则匹配 + 容错，解析失败只丢失一次数据点不影响训练 |
| 旧 preset.json 不兼容 | 加载时对新字段使用默认值兜底 |
| 导出格式参数组合复杂 | 每种格式独立参数面板（QStackedWidget），互不干扰 |
| main.py 拆分后信号连线断裂 | Phase 1 纯重构需完整回归测试再进入 Phase 2 |
