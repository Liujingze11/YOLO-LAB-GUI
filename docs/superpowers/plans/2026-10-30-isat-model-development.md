# ISAT 模型开发板块实施计划

> **For agentic workers:** Use superpowers:executing-plans, one agent only. 用户已明确授权开始，不再重复方案审批。旧 Electron 计划已停止。

**Goal:** 在原版 ISAT 内增加可运行的 YOLO 模型开发板块，并贯通已保存标注到训练。

**Architecture:** MainWindow 保持 ISAT 原实现，增加导航控制器和复用原 AnnotationView 的堆栈。模型开发使用 PyQt5 适配的现有六页；算法以固定脚本子进程执行。

**Tech Stack:** Python 3.10、PyQt5、已有 Matplotlib / Ultralytics / SAM。

**Spec:** docs/superpowers/specs/2026-10-30-isat-model-development-design.md

## Global Constraints

- 单代理顺序开发；原 ISAT 画布、菜单、插件与格式不重写。
- 只使用 PyQt5 界面；不升级已有 Python 环境。缺少的启动依赖优先用本项目独立 overlay。
- 保留既有 ISAT/software.yaml 修改；不提交模型、环境、数据或训练输出。
- 在现有 ISAT 目录的 feature/isat-model-development 分支实现；不搬迁仓库。
- GUI / CLI 独立保留；不重新创建已删除的远程仓库，不推送。

## Review Focus

1. 六页的 Qt 绑定、Matplotlib、信号签名一致；测试在真实 PyQt5 运行。
2. 标注动作在模型页意外触发、切页后 dock 和对象丢失；任务 2 实测。
3. 数据缺标注、重名来源、类别不匹配或半途中止；任务 3 用字节与输出清单检查。
4. 停止发生在进程刚启动前、无日志或子孙进程阻塞；任务 1 测真实子进程。
5. GPU 与 SAM 冲突、关闭后孤儿进程；任务 2/4 检查并明确硬件验证限制。

## Task 1: 模型开发六页的 PyQt5 适配

**Files:** ISAT/model_development/{widget.py,gui/,core/,tools/,locales/,PROVENANCE.json}；tests/model_development/test_widget.py、test_workers.py。
**Interfaces:** ModelDevelopmentWidget(QWidget) 提供 train_tab、infer_tab、export_tab、tabs、active_workers()、stop_workers()；后台 Worker 继续输出日志、进度、完成和取消信号。

- [x] 先写失败检查：真实六页加载，训练配置表单往返，导出格式和工具入口存在，主进程未加载 PySide6；真实静默子进程取消不阻塞 UI 且后代退出。
- [x] 运行 QT_QPA_PLATFORM=offscreen Python unittest 确认 RED。
- [x] 按原 GUI 文件精确迁移，改命名空间及 Qt 绑定；可写数据放应用数据目录；记录来源摘要。修复为适配而遇到的运行问题，不删除旧功能。
- [x] 运行测试 GREEN；提交本任务（不含 software.yaml）。

## Task 2: 接到 ISAT 主窗口与导航

**Files:** ISAT/model_development/integration.py、ISAT/widgets/mainwindow.py、tests/model_development/test_integration.py。
**Interfaces:** install_model_development(mainwindow) -> controller；controller.show_annotation() / show_development()；复用 mainwindow.view 和 scene。

- [x] 先写真实 Qt 窗口切页检查：视口/对象保持；原隐藏 dock 保持隐藏；标注快捷键在模型页不生效，返回恢复。
- [x] 添加固定导航、懒加载六页和关闭任务处理；保持原主窗口与启动入口。GPU 任务预检处理 SAM 冲突。
- [x] 用临时设置和代表图片实际构造 ISAT 主窗口、切页、保存截图；确认原 software.yaml 摘要未变后提交。

## Task 3: 当前标注数据准备训练集

**Files:** ISAT/model_development/{dataset.py,dataset_dialog.py}、tests/model_development/test_dataset.py。
**Interfaces:** prepare_dataset(image_root, label_root, destination, categories, val_ratio, seed, check_cancelled) -> {data_yaml,train,val,skipped,warnings}；窗口完成后填入 train_tab 数据路径。

- [ ] 先写缺标注不入集、同种子划分相同、原 JSON/图片不变、中文路径及失败不发布的测试并运行 RED。
- [ ] 用原 YOLO 转换规则导出，保留 ISAT 主档，固定类别，复制图片，临时目录原子发布；异步进度与取消。
- [ ] 从 ISAT 窗口保存并准备数据，再验证 YAML 已进入训练表单；GREEN 后提交。

## Task 4: 真实任务、回归与说明

**Files:** tests/model_development/、docs/superpowers/verification/、README.md、启动脚本。
**Interfaces:** 以正常启动入口运行；不需要原 GUI 源码目录或 Electron。

- [ ] 使用已有本地权重和临时数据集执行 CPU 一轮训练、推理；可用导出后端单独验证，缺依赖明确记录。
- [ ] 运行全部新测试；核查原 ISAT 代码差异、所有迁移入口和进程退出；记录 GPU / SAM 真机未验证边界。
- [ ] 更新中英文 README 与启动命令，单代理整分支自审并修复重要问题，保留可检查的截图和运行日志；提交。
