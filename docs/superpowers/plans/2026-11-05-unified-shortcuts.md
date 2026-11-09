# Unified Shortcuts Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement sequentially in the existing working tree.

**Goal:** 全局快捷键入口和按功能分页的设置窗口。
**Architecture:** 共享校验与原子 JSON 设置，保留旧配置作为初始值；统一分页窗口由工作台控制器连接各功能动作。
**Tech Stack:** Python、PyQt5、unittest。
**Spec:** `docs/superpowers/specs/2026-11-05-unified-shortcuts.md`

## Global Constraints

- 单代理顺序开发；不提交或推送；不修改个人 software.yaml。
- 三个功能的快捷键上下文隔离；已有设置可继续读取。

## Review Focus

- 在筛选页编辑标注快捷键后，标注动作不能提前启用，回到标注恢复新值。
- 没有创建工作页时也能修改设置；工作页首次创建及项目切换重建后要加载新值。
- 同页冲突、无效组合、类别数字保留键、存储失败必须保持原设置。
- 隐藏的标注窗口重载配置不能绕过快捷键隔离。
- 小屏幕、深色主题、长标注操作列表需可读可滚动。

### Task 1: 设置与分页窗口

**Files:** new `ISAT/shortcuts.py`, new `ISAT/widgets/workspace_shortcuts_dialog.py`, `ISAT/data_screening/shortcuts.py`, new `tests/test_workspace_shortcuts.py`。
**Interfaces:** `ShortcutSettings(commands, filename, path=None, bindings=None, reserved=())`；`annotation_settings(window)`；`development_settings()`；`ShortcutPage(key, title, settings, save)`；`WorkspaceShortcutsDialog(pages, current, parent)`。
- [x] 添加迁移、校验、存储失败、草稿/恢复/分页保存测试并观察失败。
- [x] 实现共享设置和可滚动分页窗口；保留筛选独立组件的兼容入口。
- [x] 运行设置与对话框测试。

### Task 2: 全局入口与工作区隔离

**Files:** `ISAT/model_development/integration.py`, `widget.py`, `ISAT/widgets/mainwindow.py`, `ISAT/data_screening/widget.py`, integration tests, theme。
**Interfaces:** controller `show_shortcuts(page=None)` / `create_shortcut_dialog(page=None)` / `set_annotation_shortcuts(bindings)`。
- [x] 添加全局入口、保存并切换、懒加载和原菜单路由集成测试并观察失败。
- [x] 统一入口、移除局部按钮，接入各页保存和标注重载保护。
- [x] 运行相关回归与全量测试，渲染并检查三个分页和入口截图。
- [x] 自审差异、更新验证记录与使用说明。
