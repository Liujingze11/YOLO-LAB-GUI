# Project Home Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** 清晰的新建/打开入口，以及保留原数据的自动识别整理。
**Architecture:** 复用 WorkspaceHome、WorkspaceStore 和筛选导入流程；新增可取消的后台操作及 YOLO 副本整理模块。识别元数据用于卡片和打开结果提示。
**Tech Stack:** Python 3.10、PyQt5、Pillow、PyYAML、unittest。
**Spec:** `docs/superpowers/specs/2026-11-05-project-home.md`

## Global Constraints

- 原生 PyQt5；单代理顺序开发；当前 feature 分支原地修改。
- 原文件不变、重开复用副本、取消不留下半成品，不覆盖已有工作。
- 保留本会话筛选页简化及其他未提交改动，不提交个人设置，不推送。

## Review Focus

- 更改新建位置后校验必须按新位置计算，取消浏览不改变字段。
- 同名图片及跨 split 同名图片不能覆盖；图片/标签名称对应。
- 类别字典乱序时编号仍保持一致；无标签图片不生成伪标签。
- 复制取消或源文件变化时清理临时目录，已有项目不受影响。
- 多候选配置、失效目录、未保存标注及后台任务不能错误切换。

### Task 1: 首页与新建弹窗

**Files:** `ISAT/workspaces/home.py`, `store.py`, `tests/workspaces/test_home.py`, `test_integration.py`。
**Interfaces:** `WorkspaceHome.create_button/open_button`；`CreateProjectDialog.location_edit/location`；`WorkspaceStore.creation_location()/remember_creation_location(location)`。
- [x] 更新现有入口测试，增加位置修改、默认位置恢复和卡片可区分性测试，运行确认失败。
- [x] 实现顶部入口、纯项目卡片、可编辑位置的新建弹窗和成功后位置记忆。
- [x] 运行 HomeTests，确认取消无文件写入、回车只创建一次、窄窗口正常布局。

### Task 2: 自动识别与整理

**Files:** `ISAT/workspaces/external.py`, new `organize.py`, `tests/workspaces/test_external.py`, new `test_organize.py`。
**Interfaces:** `recognize(root, check_cancelled=...)` 返回类型、数量；`organize_yolo(info, check_cancelled, progress)` 返回工作副本 data.yaml。
- [x] 编写识别计数、多配置歧义、保留 split/类别、重复名称、取消清理和源文件保持原样的失败测试。
- [x] 实现识别统计与 YOLO 原子副本整理，保留未标注状态及编号，复用已完成副本。
- [x] 运行 external/organize 测试并检查所有源文件字节未变。

### Task 3: 后台打开流程与交付

**Files:** new `ISAT/workspaces/operations.py`, `home.py`, `integration.py`, `store.py`, integration tests, README。
**Interfaces:** `run_operation(parent, title, operation)`；`WorkspaceHome.location_ready(dict)`；`open_workspace(root, detected=None)`。
- [x] 编写后台取消、YOLO 工作副本接入训练、重开复用及守卫测试并确认失败。
- [x] 接入后台识别/整理，识别结果随打开传递；展示来源类型、数量与副本位置；更新文档。
- [x] 运行工作空间与筛选集成测试、全量 tests，检查差异，捕获并查看首页/新建/打开结果截图。
- [x] 记录验证和局限，完成自审与交付。
