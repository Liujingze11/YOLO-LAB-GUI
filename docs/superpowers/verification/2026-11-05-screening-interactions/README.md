# 筛选交互验证（2026-11-05）

## 完成内容

- 图片列表与回收站采用原生多选：空白处框选、Ctrl+单击增减、Shift+单击连续选择、Ctrl+A 全选。不增加勾选框或选择模式按钮。
- 从已选缩略图拖动整个选区，图片区与回收站可以双向移除／恢复；回收站折叠标题接受拖入并展开，落点显示蓝色提示。
- 对比预览点击哪侧，方向键、底部按钮和序号控制哪侧，另一侧保持不变。蓝色细边框显示活动侧；按实际预览路径翻页，跳过另一侧图片，到边界停止。外部图或空对比区可从列表首／尾开始切换。
- 删除底部“退出对比”按钮；Esc、可自定义的退出快捷键、右键菜单及原有拖回列表操作保留。
- 移除主图时保留有效对比图；只剩对比图时提升为单图。恢复无关照片保留现有两张预览。

## 验证

- 筛选控件测试从 31 项增加至 45 项。旧代码首轮 41 项运行出现 6 个预期失败，覆盖右侧导航、双向拖放、路径导航、退出按钮及恢复时保留对比；原生 Ctrl／Shift／框选行为已通过，直接沿用。
- 修复实现回归：`setMovement(Static)` 会清除原生拖动与 viewport 落点标志，必须在列表布局设置后启用。补充实际 mousePress/mouseMove 发起拖动，确认两侧都能整组传递。
- 覆盖忙碌期间拒绝、外部图片／过期会话／重复 ID／错误载荷、同区拖动、取消不移除、原文件字节不变、全部移除与恢复、左右焦点切换、按钮跟随、快速连续按键及自定义按键。
- 最终全量 unittest **212 项通过，0 失败，40.506s**。`git diff --check` 通过。
- 单代理自审：校验会话 ID 和记录归属后复用 session.remove/restore；拖放不直接移动文件。自审发现向外部程序提供 MoveAction 会允许移出项目文件，先加入失败测试，再改为仅提供 CopyAction，内部移除／恢复仍由应用处理。最后全量回归通过。
- MainWindow 测试隔离项目和配置，校验个人 software.yaml 哈希不变；不提交或推送。

```bash
QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/yolo-screening-interactions-mpl PYTHONPATH=.runtime/python:. /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest discover -s tests -v
```

## 界面检查

- [多选与右侧活动预览](01-comparison-selection.png)
- [折叠回收站展开为拖放落点](02-trash-drop-target.png)
- [回收站多选](03-trash-selected.png)
- [深色模式](04-dark.png)
- [1000 × 720 窄窗口](05-narrow.png)

截图来自真实 MainWindow 离屏渲染并逐张检查。鼠标选择、Qt 拖入事件及键盘导航使用实际控件；原生 QDrag 平台循环在自动化测试中替换为真实接收方事件分发，尚未人工验证 Wayland/X11 桌面的跨窗口拖动手感。

## 自由拖动追加验证

- 对比左右图片互拖直接互换；拖回自身或将同一主图拖入空对比区保持不变。互换不退出对比，并把方向键操作焦点交给落点侧。
- 互换复用 QPixmap，保留缩放与场景中心，已加载图片无需新建 PreviewWorker。测试覆盖一侧出现竖向滚动条而另一侧没有的情况；使用 AnchorViewCenter 避免布局改变导致偏移。
- 缩略图按下时先保留当前预览，单击释放才切图；开始拖动或取消拖动不会临时跳成另一张图。
- 项目预览可拖入回收站，回收站单图拖入任意预览侧会恢复并显示；外部图和旧会话预览不能移入项目回收站。预览拖回图片列表的原有操作继续通过。
- 全量测试从 212 项增加至 **220 项，全部通过（41.533s）**；筛选控件共 53 项。初始新增用例确认 5 个缺失行为失败，之后修复；另增加空对比区、自身拖动、原生鼠标拖起后再按方向键的覆盖。`git diff --check` 通过。
- 捕获并检查真实主窗口新增截图：[互换提示](06-swap-hint.png)、[互换结果](07-swapped.png)、[深色提示](08-swap-hint-dark.png)、[恢复提示](09-restore-hint.png)、[恢复到预览](10-restored-preview.png)。仍未对真实 Wayland/X11 桌面拖动帧率作人工测量。

本轮全量命令与上节相同，`MPLCONFIGDIR=/tmp/yolo-screening-drag-flow-mpl`。

## 单图左右加入对比追加验证

- 单图左右各 28% 区域均接收对比：新图落在哪侧就显示在哪侧，原图显示在另一侧；中央仍用于替换。拖动经过左、中、右区域实时更新对应提示，松手前不改变预览。
- 左侧加入对比复用原图的 QPixmap 与缩放／场景中心，只为新图创建一次预览加载；右侧行为保持一致。回收站单图可在两侧恢复并对比，自身边缘拖入保持单图；已排队的旧加载结果不会覆盖最终图片。
- 新增 4 项控件测试，先确认旧行为失败；最终筛选 **57 项**、全量 **224 项通过（41.818s）**。`git diff --check` 通过；个人 software.yaml 仍为原有 3 行增加／1 行删除。
- 已逐张检查实际主窗口截图：[左侧落点提示](11-left-compare-hint.png)、[左侧对比结果](12-left-compare-result.png)、[右侧落点提示](13-right-compare-hint.png)、[右侧对比结果](14-right-compare-result.png)、[深色窄窗口提示](15-left-compare-hint-dark-narrow.png)。落点提示清晰，双图等宽，活动侧与新图一致。
- 本轮全量命令同上，`MPLCONFIGDIR=/tmp/yolo-screening-both-edges-mpl`，日志 `/tmp/yolo-screening-both-edges-full.log`。仍使用实际 Qt 控件离屏验证，未测量真实桌面拖动帧率。
