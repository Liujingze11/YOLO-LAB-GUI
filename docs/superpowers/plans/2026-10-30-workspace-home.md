# 工作空间启动首页 Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. 按既有单代理原地开发要求执行，不创建 worktree、提交或推送。

**Goal:** 软件启动展示带照片的工作空间卡片，先选择保存位置创建空间，再进入原生工作台。

**Architecture:** 新增工作空间存储、首页组件及其控制器，接入现有 ModelDevelopmentController 的原生页面栈。保留筛选项目格式；每个空间保存独立训练草稿、输出默认路径和封面。

**Tech Stack:** Python 3.10、PyQt5、Pillow、YAML、unittest。

**Spec:** `docs/superpowers/specs/2026-10-30-workspace-home-design.md`

## Global Constraints

- 原生 PyQt5，保留既有未提交修改，单代理原地开发，不提交或推送。
- 新建先选择父目录，再输入名称；取消不写文件，同名不覆盖。
- 返回首页保留当前画布和后台任务；切换空间处理未保存内容及后台任务。
- 兼容现有 projects 结构；训练封面来自实际 data.yaml，缓存到空间内。

## Review Focus

- 目录取消、空名称及同名目录：不创建或覆盖用户文件。
- 最近目录丢失、损坏元数据：首页继续可用并显示错误。
- 切换空间：标注、筛选、后台任务不会丢失或被静默替换。
- 缺图片或无训练：封面降级正常，新空间可直接进入。
- 重启与多空间：训练参数及输出目录互不混用，配置测试使用临时目录。

### Task 1: 工作空间存储与封面

**Files:** 新增 `ISAT/workspaces/store.py`、`tests/workspaces/test_store.py`。

**Interfaces:** `WorkspaceStore.create(parent, name)`、`register(root)`、`recent()`、`read(root)`、`update(root, **fields)`、`set_cover(root, image, trained=False)`；`training_image(data_yaml)` 返回实际训练图片或 None。

- [x] RED：验证创建、重复/无效名称、重开历史、旧空间、损坏/缺失记录及相对 YAML/TXT 图片路径。
- [x] GREEN：实现原子元数据和最近记录、缓存缩略图，不变更旧项目格式。

### Task 2: 原生卡片首页与创建流程

**Files:** 新增 `ISAT/workspaces/home.py`、`tests/workspaces/test_home.py`。

**Interfaces:** `WorkspaceHome(store)` 发出 `workspace_requested(str)`；`refresh()` 重载卡片；`create_workspace()` 先目录后名称，`open_workspace()` 选择已有目录。

- [x] RED：空首页、新建顺序/取消、卡片点击、已有空间打开。
- [x] GREEN：实现可滚动自适应卡片布局、品牌和封面、路径不可用状态。

### Task 3: 工作台接入与独立状态

**Files:** 新增 `ISAT/workspaces/integration.py`，修改 `ISAT/model_development/integration.py`、`ISAT/data_screening/widget.py`、`ISAT/model_development/gui/tabs/train_tab.py`、`ISAT/widgets/mainwindow.py`。

**Interfaces:** `WorkspaceHomeController(controller)` 提供 `show_home()`、`open_workspace(root)`、`configure_development(widget)`、`record_training(config)`、`save_current()`；筛选发出 `session_loaded(object)`，训练发出 `training_started(object)`。

- [x] RED：启动默认首页，同空间往返保留状态，多空间输出/草稿隔离，未保存取消和后台任务守卫。
- [x] GREEN：接入首页导航、恢复最近项目、按空间设置数据集和输出默认路径，训练时更新封面，关闭时保存草稿。

### Task 4: 完整验证与交付

- [x] 运行 `QT_QPA_PLATFORM=offscreen PYTHONPATH="$PWD/.runtime/python:$PWD" /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest discover -s tests -v`。
- [x] 使用临时工作空间生成实际首页、创建和进入工作台截图，检查不同宽度及原生菜单操作。
- [x] 检查 diff、原配置 hash，更新 README 和验证记录，说明实际测试结果。
