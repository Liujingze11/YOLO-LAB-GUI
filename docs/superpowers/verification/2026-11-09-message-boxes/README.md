# 提示框统一与溢出处理

## 改动

- 在工作台主题初始化时安装一次全局提示框样式，覆盖筛选、标注、模型开发、项目管理以及调用原生 QMessageBox 的插件；无需逐处替换原有调用。
- 统一 14px 字体、留白、按钮高度、明暗背景、默认操作和危险操作颜色。中文界面的标准按钮及详情按钮显示中文；自定义操作保留原文和角色。
- 正文自动换行，长路径可按字符换行；超长内容在框内滚动。可用屏幕尺寸决定布局，按钮始终在正文之外。
- 详情列表独立滚动，展开后重新计算嵌套布局，避免正文被旧的详情高度挤压。原生按钮返回值、默认键、Escape、关闭与保存流程不变。
- 标注未保存时的退出提示支持中文；设置窗口、输入窗口和系统文件选择器不受此次提示框处理影响。

## 验证

- 原始默认短保存提示未复现越界；70 行错误正文可复现 1852px 高的弹窗超出 600px 可用屏幕，长路径也可导致超高窗口。
- 全量 **242 项测试通过（52.762s）**。新增 9 项真实 Qt 控件测试覆盖长正文、长路径、跨页面样式隔离、明暗主题、四类静态提示、默认/取消行为、危险按钮与详情、重复显示/富文本、英文与自定义操作。
- 提示框专项测试在 **150% 和 200% 缩放下均 9/9 通过**，200% 离屏可用尺寸为 400 × 300 逻辑像素。
- 使用完整 MainWindow 复核退出标注提示，并捕获筛选保存和后台任务提示；取消后主窗口保持打开。集成测试仍检查个人 software.yaml 内容未变。
- Python 语法检查及 `git diff --check` 通过。自审检查了原生标签生命周期、详情按钮翻译尺寸、重复打开时的布局重建和布局事件收敛。
- 截图来自真实 Qt 控件离屏渲染；未操纵或关闭用户正在使用的窗口。

```bash
QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/yolo-messageboxes-mpl PYTHONPATH=.runtime/python:. /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest discover -s tests -v
QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=1.5 PYTHONPATH=.runtime/python:. /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest tests.test_message_boxes -v
QT_QPA_PLATFORM=offscreen QT_SCALE_FACTOR=2 PYTHONPATH=.runtime/python:. /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest tests.test_message_boxes -v
```

## 截图

- [保存提示](01-save-light.png)
- [深色详情](02-details-dark.png)
- [200% 缩放长正文](03-long-200-percent.png)
- [200% 缩放详情展开](04-details-200-percent.png)
