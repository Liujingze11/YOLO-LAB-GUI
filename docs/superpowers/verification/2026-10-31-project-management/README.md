# 项目管理验证

后续修正：目录删除增加创建来源及目录身份验证，旧版或已有目录仅支持从列表移除；桌面等位置受保护，命名改为初始为空且必填，卡片尺寸统一。最新结果见[项目目录保护验证](../2026-10-31-project-safety/README.md)。

2026-10-31，按用户最新要求恢复命名步骤，并加入项目右键管理。当前分支原地修改，保留已有改动，没有提交或推送。

## 行为

- 新建：选择保存位置 → 输入项目名称 → 创建同名子文件夹并自动进入工作台。取消不写入，同名不覆盖。
- 项目右键：打开项目、打开文件夹、复制路径、删除项目。删除确认后将整个项目文件夹移入系统回收站；失败保留原项目。
- 项目目录或项目标记被外部删除后，刷新或重新打开首页不再显示该卡片。退出和延迟回调不会重新创建已删除的项目。
- 删除当前项目会处理未保存内容，任务运行时阻止删除；完成后清理当前项目引用。兼容已有旧版工作空间。

## 验证

完整回归 **107 项测试通过**（21.652 秒），[测试输出](tests.log)。

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH="$PWD/.runtime/python:$PWD" \
  /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest discover -s tests -v
```

[原生界面验证脚本](verify_ui.py)使用真实 MainWindow、目录选择框、命名弹窗、右键菜单及删除确认框；实际调用 `QFile.moveToTrash`，确认回收站保留项目文件，关闭程序后项目目录未重建。也检查了外部删除后卡片消失。[界面验证输出](ui.log)。

- [命名与最终保存路径](project-name.png)
- [创建后自动进入工作台](created-workbench.png)
- [项目首页](home.png)
- [右键菜单](context-menu.png)
- [删除确认](delete-confirmation.png)

界面验证使用临时项目、临时配置及独立的 `XDG_DATA_HOME`，回收站测试只移动合成数据。`git diff --check` 通过；原 `ISAT/software.yaml` SHA256 保持 `a538c2368fe057a70b13bb61b709bf0cd94ce31f6a0b3dca39a9179ee7ba7fa0`。

本次验证项目管理流程及现有回归测试，没有运行 GPU 训练。
