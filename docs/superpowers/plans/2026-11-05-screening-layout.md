# Screening Layout Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans sequentially in the existing checkout.

**Goal:** 用户已确认的导入空状态与紧凑筛选工作区。
**Architecture:** 用一个 stacked widget 切换导入页和原有工作区；公共任务行独立于两种状态；回收站按数量及用户折叠状态更新。
**Tech Stack:** Python、PyQt5、unittest。
**Spec:** `docs/superpowers/specs/2026-11-05-screening-layout-design.md`

## Constraints / Review Focus

- 本地单代理；不提交或推送，不改个人 software.yaml。
- 失败、取消后能重新导入；导入中取消按钮必须可见。
- 全部移除后仍能恢复；隐藏/展开回收站不丢失条目和选择。
- 外部预览、拖回列表、对比不能显示错误的列表序号。
- 窄窗口、深色主题、三列缩略图和等宽对比需验证。

### Task 1: 界面状态与布局

**Files:** `ISAT/data_screening/widget.py`, `views.py`, `ISAT/ui_theme.py`, `tests/data_screening/test_widget.py`。
**Interfaces:** `empty_page`, `empty_open_button`, `content_stack`, `list_header`, `position_label`, `trash_toggle`, `_sync_layout_state()`；`FolderDropArea.folder_dropped`。
- [x] 为初始导入、按钮及拖入后工作区、取消重试、失败重试、空/非空回收站、预览序号添加失败测试。
- [x] 实现原生布局与状态同步，保留数据及现有事件处理。
- [x] 运行筛选测试和工作台相关集成测试，修正任何退化。

### Task 2: 视觉与回归验证

**Files:** README、`docs/superpowers/verification/2026-11-05-screening-layout/`。
- [x] 渲染并查看空状态、导入后、回收站、对比、深色和窄窗口截图。
- [x] 按实际截图修正布局，运行适用回归测试并进行代码自审。
- [x] 更新使用说明、验证记录和完成状态。
