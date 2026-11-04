# SDD ledger — plan: docs/superpowers/plans/2026-10-30-screening-viewer-controls.md

Spec: docs/superpowers/specs/2026-10-30-screening-viewer-controls.md
Ruling: 执行用户已确认的三点及快捷键可改保存，按现有单代理方式继续，不新增审批轮次或代理。
Pre-flight: ShortcutSettings 产出归一化绑定，由页面共用 QAction 消费；视图 MIME 路径交给页面启动独立 PreviewWorker；集成层必须排除页面自身拥有的 QAction。
Preferences baseline: a538c2368fe057a70b13bb61b709bf0cd94ce31f6a0b3dca39a9179ee7ba7fa0。

Task 1: complete — ShortcutSettings 三项测试从缺少模块 RED 到 GREEN；真实改键按键、菜单复制路径、设置窗口保存/取消测试通过。配置原子替换，冲突时保留原文件与运行绑定。
Task 2: complete — 新拖放/对比测试从缺少接口 RED 到 GREEN。三列测试复现 QListView 在格子恰好占满 viewport 右边缘时换行成两列，保留一像素余量后宽窄均通过。额外覆盖关闭迟到结果、快速替换与预览焦点下按左右切图。
Task 3: complete — 全套 53 项通过，12.277 秒。工作区自身 QAction 隔离测试通过；Qt isAncestorOf 包含自身，仍将自身判断显式写出。实际界面截图已保存，对比宽度 408/407，首三项在同一行、第四项在下一行。
Self-review: 单代理约束优先，未分派审查代理。检查拖动前主图快照、异步 revision、线程取消/关闭、上下文路径与原图保持、快捷键持久化及菜单一致性，无未处理阻断项。
Verification: 当前软件配置哈希未变；测试快捷键写入临时目录，没有修改用户快捷键配置。没有推送或改动其他仓库。
