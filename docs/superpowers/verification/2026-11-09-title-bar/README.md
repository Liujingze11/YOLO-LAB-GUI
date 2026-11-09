# 标题栏合并验证

- 顶部改为一行：左侧快捷键、居中项目名、右侧最小化/最大化/关闭；原独立快捷键工具栏移除。
- 全部工作页复用现有快捷键对话框；项目名随窗口标题更新。长标题省略，悬停可看完整名称。
- 使用 Qt 系统移动/缩放接口，提供不支持这些接口时的拖动和边缘缩放回退。最大化/全屏关闭边缘热区，手动缩放尊重最小/最大尺寸。
- 关闭按钮调用原窗口 close()；真实主窗口未保存标注提示选择取消后仍保持打开。
- 明暗主题与窗口按钮同步；保留键盘焦点和可访问名称。

## 验证结果

- 修改前，既有快捷键集成测试 7/7 通过；新集成断言因主窗口没有自定义标题栏失败。
- 最终全量 `unittest discover -s tests -v`：**250 项通过，59.898s**。
- 200% 缩放标题栏测试：**7/7 通过**，包含长标题、明暗配色、最大化/还原、最小化、拒绝关闭、拖动/缩放回退、四边四角和最小宽度、原生接口调用。
- `py_compile` 和 `git diff --check` 通过。
- 真实 MainWindow 使用临时项目及配置离屏渲染，集成夹具检查个人 software.yaml 哈希未变。
- 单代理自审发现标题标签为了拖动而设置鼠标穿透，导致完整名称提示无法出现；用真实 QHelpEvent 复现失败，将提示放到实际接收鼠标的标题栏后通过，随后重新运行全量测试。
- 自审检查了页面菜单保留、关闭保护、边缘热区和子对话框隔离。按项目单代理约定自行审查；不提交或推送已有迁移工作区。

桌面窗口管理器实际接管后的移动、贴边和系统阴影未做桌面实测；本次验证为 Qt 离屏控件行为、系统接口调用契约及回退逻辑。

## 复现

```bash
QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/yolo-titlebar-suite-mpl PYTHONPATH=.runtime/python:. /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=2 PYTHONPATH=.runtime/python:. /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest tests.test_title_bar -q
QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/yolo-titlebar-capture-mpl PYTHONPATH=.runtime/python:. /home/ljz/miniconda3/envs/isat_env/bin/python docs/superpowers/verification/2026-11-09-title-bar/capture.py
```

## 截图

- [标题栏](title-bar.png)
- [首页](01-home.png)
- [项目筛选页](02-project.png)
- [快捷键窗口](03-shortcuts.png)
- [标注页](04-annotation.png)
- [深色开发页](05-dark.png)
- [长项目名](06-long-title.png)
