# 回车创建与默认名称验证

2026-11-02，按最新要求替代此前名称初始为空且必填的行为。在当前分支单代理原地修改，保留已有工作，没有提交或推送。

- 选择保存位置后，名称初始为可编辑且全选的“新项目”。名称已被文件、目录或悬空符号链接占用时，自动顺延为“新项目 2”等。
- 清空名称或只填空格时，预览和提交使用同一个可用默认名称；自定义非法/已占用名称仍不可提交。
- Return 和小键盘 Enter 创建独立子文件夹并进入数据筛选工作台；单次按键只发出一次 accepted 信号。
- 原模型层有效名称检查、排他创建、目录保护和删除归属判断保留。取消不写文件，所选父目录不会直接成为项目，也不覆盖原项目。

## 原生回车问题

真实 X11 窗口复现：有首页样式的按钮框尚未加入弹窗布局就设置默认按钮，显示后“取消”会成为默认按钮，回车返回 Rejected。独立无样式弹窗和此前 offscreen 测试未暴露此行为。

最小对比中，把设置默认按钮移到加入布局之后，Return 返回 Accepted。最终实现沿用 Qt 的默认按钮机制，没有额外连接 returnPressed；带首页样式的父窗口下，Return/Key_Enter 均检查单次 accepted 且没有 rejected。

[原生失败测试](native-red.log)、[修复后同一测试](native-green.log)。默认名称的初始 RED 见 [red.log](red.log)。

## 验证结果

完整回归 **149 项通过，30.351 秒**，见 [完整输出](tests.log)。

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH="$PWD/.runtime/python:$PWD" \
  /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest discover -s tests -v
```

[原生界面脚本](verify_ui.py)以 `QT_QPA_PLATFORM=xcb` 运行，使用真实目录选择框和命名弹窗，在临时位置依次操作：默认名 + Return；清空名称 + 小键盘 Enter；自定义名称 + Return；取消下一次创建。验证前三次均进入工作台、最近卡片名称正确、没有重复提交、父目录没有项目标记、原有文件及前一个项目数据保持不变。见 [界面输出](ui.log)。

- [默认名称](default-name.png)
- [清空名称仍预览有效子目录](blank-name.png)
- [回车进入工作台](entered-workbench.png)
- [创建后的首页](home.png)

已目视检查默认名称弹窗和实际工作台截图。`git diff --check` 通过，原 `ISAT/software.yaml` SHA256 保持 `a538c2368fe057a70b13bb61b709bf0cd94ce31f6a0b3dca39a9179ee7ba7fa0`。全部创建/取消操作仅使用临时合成数据。
