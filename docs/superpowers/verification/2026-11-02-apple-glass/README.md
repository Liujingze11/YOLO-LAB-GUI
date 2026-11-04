# 苹果风格玻璃外观验证

2026-11-02。按用户要求对现有原生 PyQt5 软件整体换肤，并移除截图中的左侧“工作空间”入口。保留当前目录全部已有修改，单代理完成，没有提交或推送。

## 界面变化

- 首页、侧栏、筛选列表、预览容器、标注停靠面板、模型参数卡片和原生弹窗采用统一浅色玻璃材质。
- 窗口内柔光背景透过半透明面板可见；圆角、高光边框、低强度阴影和蓝色状态反馈统一。图片、轮廓和控件文字不使用透明度效果。
- 侧栏按原顺序保留返回首页、数据筛选、数据标注、模型开发。筛选页原有工作空间按钮保留；其余功能及按钮所在区域不重排。
- 模型页保留深色切换；导出格式卡片及设置说明同步变色。下拉框与数字控件采用可见的明暗箭头。
- 中文侧栏宽度保持 88，英文长标签可以扩展，不强制裁切。首页卡片继续为 300×284。

此效果为窗口内部的透明材质和柔光绘制，不调用操作系统桌面模糊接口；没有新增依赖，也不模糊真实图片。

## 原生界面证据

[验证脚本](verify_ui.py)使用临时项目与独立配置，在 X11 原生窗口完成命名回车、图片筛选导入、两条原生标注轮廓恢复、六个模型页面、明暗切换、数字箭头点击、导出格式点击、1100×760 小窗口和英文导航检查。未启动训练或导出任务。

- [首页](home.png)、[新建弹窗](create.png)
- [数据筛选](screening.png)、[数据标注](annotation.png)
- [训练](train.png)、[推理](infer.png)、[数据转换](export.png)
- [日志结果](logs.png)、[工具](tools.png)、[设置](settings.png)
- [深色训练](train-dark.png)、[深色转换](export-dark.png)、[深色设置](settings-dark.png)
- [小窗口筛选](screening-small.png)、[小窗口训练](train-small.png)、[英文导航](navigation-en.png)

改版前基线在 [before-geometry.json](before-geometry.json)，改版后在 [geometry.json](geometry.json)。相同 1440×960 窗口下，侧栏及记录的筛选页打开、重命名、移入回收站、保存、导入、工作空间按钮和主分割区，坐标及尺寸逐项完全相同。原布局结构和模型页尺寸常量保留；字体与边框会影响其他控件的自然尺寸，不声称每个内部像素都相同。

## 回归与自查

完整回归 **150 项通过，32.775 秒**，见 [测试输出](tests.log)。新增导航行为检查验证四个入口及原页面切换，既有项目、默认命名、键盘回车、数据保护、标注和训练参数测试均通过。

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH="$PWD/.runtime/python:$PWD" \
  /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest discover -s tests -v

QT_QPA_PLATFORM=xcb PYTHONPATH="$PWD/.runtime/python:$PWD" \
  /home/ljz/miniconda3/envs/isat_env/bin/python \
  docs/superpowers/verification/2026-11-02-apple-glass/verify_ui.py
```

[界面输出](ui.log)。截图已逐页检查，修正了筛选按钮的尺寸偏移、紧凑标注按钮留白、深色说明及复选框文字对比度和缺少箭头的问题。英文导航检查等待 Qt 完成布局后验证实际宽度。

按本地单代理约定进行作者自查：背景层不接收鼠标和焦点；主题不改训练/文件操作；导出卡片仅调整样式状态；新 SVG 随现有 `ISAT/ui` 打包规则包含。`git diff --check` 通过。原 `ISAT/software.yaml` SHA256 保持 `a538c2368fe057a70b13bb61b709bf0cd94ce31f6a0b3dca39a9179ee7ba7fa0`。
