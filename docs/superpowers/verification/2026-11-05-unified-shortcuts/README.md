# 统一快捷键设置验证（2026-11-05）

## 实现

- 系统标题栏下方左上角固定“快捷键”入口：首页、筛选、标注、模型开发均可用。
- 一个窗口，数据筛选 / 数据标注 / 模型开发三个分页；从功能页打开时自动选中对应分页。
- 每页单独保存、恢复默认，逐项清空；切换分页保留草稿，关闭未保存草稿可返回继续编辑。
- 筛选工具栏移除局部按钮；筛选右键菜单、标注菜单复用统一窗口。
- 同页快捷键冲突、无效按键、多个连续组合拒绝保存；跨页允许复用；标注数字 0–9 保留用于类别。
- 读取原有筛选 JSON 和标注 software.yaml 中的自定义值。新设置分别保存到用户配置目录的 screening-shortcuts.json、annotation-shortcuts.json、development-shortcuts.json；原子替换，保存失败不改变文件或正在使用的绑定。
- 修改隐藏标注页或重载配置只更新暂停的快捷键；进入标注页才恢复，避免影响筛选和模型输入。
- 模型开发分页包含已有“运行当前训练 / 推理”快捷键，默认 Ctrl+Return。

## 验证

- 全量 unittest：191 项通过（38.326s）。
- 最后调整标注加载和深色布局后，重新运行设置、筛选快捷键、工作台及工作空间相关测试：70 项通过（32.564s）。
- 新增 14 项测试涵盖旧值兼容、文件重载、原子保存失败、冲突/保留数字、多页草稿、恢复默认、关闭取消、单一窗口、全局位置、隐藏页面隔离、延迟创建/重建和真实按键触发。
- 使用真实 MainWindow 的隔离测试夹具，用户配置与项目均位于临时目录；清理时校验真实 software.yaml 的哈希保持不变。
- `git diff --check` 通过。单代理顺序自审，无提交、推送。
- 渲染检查发现深色模式滚动页默认填充浅色背景，已关闭背景填充并重新渲染确认；输入提示改为中文，标注操作按常用流程排序。

执行方式：

```bash
QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/yolo-shortcuts-mpl PYTHONPATH=.runtime/python:. /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest discover -s tests -v
```

## 截图

- [首页全局入口](home-entry.png)
- [筛选页全局入口](screening-entry.png)
- [数据筛选快捷键](screening-shortcuts.png)
- [数据标注快捷键](annotation-shortcuts.png)
- [模型开发快捷键](development-shortcuts.png)
- [580 × 400 小窗口](annotation-small.png)
- [深色模式](annotation-dark.png)

截图通过真实 PyQt5 控件离屏渲染，不包含操作系统绘制的窗口标题栏。保留原生窗口管理；入口位于其下方的应用工具栏。
