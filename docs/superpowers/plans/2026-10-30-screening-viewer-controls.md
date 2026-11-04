# 数据筛选浏览增强实施计划

> 单代理在当前 feature 分支原地实现，使用 executing-plans / TDD 顺序执行。用户确认范围后直接完成，不增加代理或新 worktree。

Goal: 右键菜单、可修改保存的快捷键、拖动等分双图对比、默认三列缩略图。
Spec: `docs/superpowers/specs/2026-10-30-screening-viewer-controls.md`
Tech stack: PyQt5 / Python 标准库，现有环境。

## Task 1 — 共用操作与快捷键

Create `ISAT/data_screening/shortcuts.py`，modify `widget.py`；tests `test_shortcuts.py` / `test_widget.py`。

- [ ] 测试：设置保存并重载、冲突和非法键拒绝且原文件不变、恢复默认取消不写配置、改键后真实按键触发重命名、复制路径和菜单一致。
- [ ] 确认 RED，实施 ShortcutSettings 和原生设置窗口、共用 QAction，再确认 GREEN。

## Task 2 — 三列网格与双图预览

Create `ISAT/data_screening/views.py`；modify `widget.py`，复用 `PreviewWorker`；tests `test_widget.py`。

- [ ] 测试：宽窄左栏均每行三张，真实 drop 后主图保留且两侧等宽，退出恢复单图，快速替换和关闭时旧后台结果不重新出现。
- [ ] 确认 RED，实施三列尺寸计算、复制语义拖拽、等权双图和后台读取，再确认 GREEN。

## Task 3 — 集成验证

Modify `integration.py`、tests integration config isolation；更新 README 和验证资料。

- [ ] 测试：进入筛选时本页 QAction 不能被标注快捷键隐藏逻辑清空，切回标注后本页快捷键不执行。
- [ ] 运行完整 unittest 套件、实际 Qt 截图、源码启动、自审异步关闭与配置持久化。保持原图和当前用户配置不变。

## Review focus

- 拖动 B 时鼠标选择先改变主图：保留拖拽前的 A。
- 对比图在读取中被替换或关闭：丢弃旧结果。
- 左侧滚动条与分隔条改变可用宽度：始终三列。
- 无效或冲突快捷键：不覆盖旧文件，不留下部分更新。
- 隐藏页与模态设置窗口：快捷键仅作用于当前工作区。
