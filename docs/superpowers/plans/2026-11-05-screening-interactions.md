# Screening Interactions Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans, sequentially in this session. User scope and repository single-agent convention govern execution.

**Goal:** 框选／组合键多选、图片区与回收站双向拖动、对比两侧独立翻页，移除退出对比按钮。

**Architecture:** views.py 负责原生选择与拖放事件，widget.py 校验会话记录并复用筛选操作，保留统一快捷键。预览维护活动侧，各自以请求中的路径进行导航。

**Tech Stack:** Python / PyQt5 / unittest.

**Spec:** docs/superpowers/specs/2026-11-05-screening-interactions-design.md

## Global Constraints

- 原生 PyQt5；原文件不改动；保留用户 software.yaml 和此前未提交修改。
- 单代理当前功能分支继续；不创建隔离副本丢失此前改动，不提交／推送。
- 不添加勾选框或“选择”按钮；保留 Esc／右键退出。

## Review Focus

- 拖动选区与原生框选不相互抢占；鼠标按下已选图不清除选区。
- 回收站折叠落点、空列表恢复、忙碌期间拒绝、重复／跨会话载荷。
- 点击右侧后，按钮抢焦点仍控制右图；左图跳过右图，边界保持。
- 预览异步完成顺序、删除当前对比图、恢复其他图时保留对比。
- 已有外部图预览、拖回列表、可自定义快捷键仍可用。

## Task 1: 多选与双向拖动

Files: ISAT/data_screening/views.py, ISAT/data_screening/widget.py, tests/data_screening/test_widget.py.
Interfaces: 缩略图列表共享会话标识和序列化载荷；接收方通过 widget 的校验回调返回有效记录，落点信号传递记录列表。FolderGrid 保留已有预览拖放信号。

- [x] 增加真实鼠标 Ctrl／Shift／框选、批量双向拖放、折叠标题落点、取消／忙碌／过期载荷及原文件不变测试。
- [x] 运行测试确认新增行为失败：`python -m unittest tests.data_screening.test_widget -q`（使用现有 isat_env/offscreen/PYTHONPATH）。
- [x] 实现共享缩略图选择与拖放；复用移除／恢复，保持有效预览和选区，主题添加落点反馈。
- [x] 重跑该测试模块，预期全部通过。

## Task 2: 双侧导航和精简控件

Files: ISAT/data_screening/views.py, ISAT/data_screening/widget.py, ISAT/ui_theme.py, tests/data_screening/test_widget.py.
Interfaces: ImagePreview.activated 信号更新 widget 活动侧，_step 依据该侧请求路径计算目标；现有命令名和快捷键配置不变。

- [x] 增加点击左右侧后真实按键独立翻页、按钮跟随活动侧、边界／外部图／空对比区、快速切换、退出无按钮、删除／恢复时对比保留测试。
- [x] 确认新测试在旧导航逻辑失败。
- [x] 实现活动侧、高亮及导航；移除 exit_compare_button 及全部引用，保留命令。
- [x] 运行筛选及快捷键／工作台回归，再运行全量测试；预期全部通过。
- [x] 实际主窗口离屏渲染浅／深色，检查多选、活动侧边框、回收站落点与精简底栏；更新验证记录和用户说明。

## 执行记录

- 已核对当前原生 ExtendedSelection、只拖单图、回收站拒绝拖放、_step 固定控制主图的现状。
- Task 1 / Task 2 共用已有 session.remove/restore 与预览 worker；不引入后台数据操作接口。

- Task 1 / Task 2: complete。首轮 41 项测试 6 项预期失败，后续筛选 45 项通过；最终全量 212 项通过（40.506s）。
- 自审修复：原生布局会清除拖放标志，调整启用顺序；对外仅提供 CopyAction，避免移出项目文件，覆盖测试先红后绿。批量成员过滤使用集合，避免大选区二次方查找。
- 界面验收：浅色、深色、1000 × 720、批量选择与落点共五张实际窗口截图已检查。完整结果见 docs/superpowers/verification/2026-11-05-screening-interactions/README.md。

## Task 3: 自由拖动追加

Files: views.py / widget.py / test_widget.py（同上）。
Interfaces: ImagePreview 快照／恢复画面与缩放状态，落点模式回调负责 swap/keep/restore 提示；预览 MIME 由 widget 附加会话身份，回收站复用记录校验。

- [x] 为两个方向互换、自身拖动、缩放平移保留、等待中互换、预览与回收站往返、取消拖动写失败测试并确认 RED。
- [x] 实现即时互换和落点反馈，补全预览记录拖放；缩略图按下暂缓预览直到单击释放，拖动取消保留旧图。
- [x] 运行筛选模块及全量回归；使用实际窗口截图检查互换落点／结果，更新说明与验证记录。预期全部通过。

- Task 3: complete。新增自由拖动测试先确认 5 个缺失行为失败，另覆盖自身拖入空对比区、滚动条布局变化及原生鼠标拖动后键盘导航。最终全量 220 项通过（41.533s）。已检查浅／深色互换提示、即时互换结果、恢复提示与恢复结果。
- Task 3 自审：画面快照使用共享 QPixmap；swap 不新建已缓存图片的 PreviewWorker。右侧预览版本号递增、左侧按请求路径过滤过期结果；AnchorViewCenter 保持不同滚动条布局下的画面中心。预览项目记录仅通过会话 ID 和记录 ID 接入已有回收流程。

## Task 4: 单图左右对称加入对比

Files: views.py / widget.py / test_widget.py（同上）。

- [x] 添加左右落点顺序、实时提示、缓存／视角复用、回收站恢复、待加载主图及自身拖动测试，确认新行为失败。
- [x] 实现左边缘对比及对称落点提示；原图移到右侧复用画面，沿用异步预览保护。
- [x] 运行筛选与全量回归，实际主窗口截图检查左右落点及结果，更新用户说明与验证记录。

- Task 4: complete。新增 4 项测试覆盖两侧落点、回收站来源、等待中主图以及自身拖入；旧行为出现 4 个预期断言失败，子用例共享回收站状态另导致 1 个后续错误，已隔离。最终筛选 57 项、全量 224 项通过（41.818s），git diff --check 通过。实际窗口左右提示／结果及深色窄窗口共 5 张截图已检查。
- Task 4 自审：新图仅创建一个 PreviewWorker，原图共享缓存并保留视角；拖动经过各区域只变更提示，松手才组成对比。已有双图模式不启用边缘分区，仍按目标侧替换或互换。
