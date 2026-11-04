# 工作空间、副本回收站与拖动验证

2026-10-30，当前 `feature/isat-model-development`，按用户要求单代理原地开发，无新 worktree、提交或推送。

## 已实现

- 左侧导航及筛选页均有“工作空间”入口，选择位置会持久保存，可打开已有筛选项目。
- 图片及有效 ISAT JSON 在导入时复制进独立项目。筛选、重命名、清理仅作用于副本。项目保存包含 images/、json/、隐藏 .trash/、项目清单；没有标注的图片不预造空 JSON。
- Delete 先逻辑移入回收站，恢复窗口支持多选。保存成功后，明确列出待清理文件并询问；拒绝清理会持久保留，可关闭重开后恢复。保存失败/取消不弹清理确认，不自动导入。
- 单图中间拖入替换、右侧提示区加入对比；双图分别替换。预览左键拖回缩略图区只撤下预览，主图撤下时提升另一张；网格仍固定三列，无重复图片。中键平移、滚轮缩放。C 打开拖入式对比区，Esc 退出。
- Ctrl+S 保存、Ctrl+Shift+T 回收站均可自定义。保留既有菜单、快捷键与原生 ISAT 标注集成；保存同一项目会刷新标注文件列表。未保存标注、SAM 忙碌或保存中的同项目均受守卫保护。

## 验证

在仓库根目录运行：

```bash
QT_QPA_PLATFORM=offscreen PYTHONPATH="$PWD/.runtime/python:$PWD" \
  /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest discover -s tests -v
```

最终 **69 项测试全部通过**，详见 [tests.log](tests.log)。覆盖原文件字节/独立 inode、逻辑回收/恢复/重开/清理、保存回滚、已有和新建标注、拖入各区域/拖回、异步陈旧结果及取消、原版画布保存与配置隔离。各 `*-red.log` 保留实施前的失败证据。

`QT_QPA_PLATFORM=offscreen timeout 7 ./run-isat.sh` 持续运行至预期的 124 超时，无 traceback，[启动日志](startup.log)。

实际原生 PyQt5 窗口截图（合成测试图片，临时工作空间和临时配置）：

- [工作空间导航与等分对比](workspace-comparison.png)
- [右边缘加入对比提示](drop-hint.png)
- [工作空间选择与项目列表](workspace-picker.png)
- [可恢复回收站](trash.png)
- [保存后的永久清理确认](delete-confirmation.png)

截图由 [verify_ui.py](verify_ui.py) 运行真实 MainWindow 生成，没有修改用户图片或全局配置。用户 `ISAT/software.yaml` SHA256 仍为 `a538c2368fe057a70b13bb61b709bf0cd94ce31f6a0b3dca39a9179ee7ba7fa0`。

## 自审与范围

遵守本目录 CLAUDE.md 的单代理要求，由实现者单独自审。检查了副本所有权、清单路径、符号链接、新回收目标、重名及保存事务；新目标含外部符号链接的情况补充 RED→GREEN 回归。所有写入/清理都验证受管路径。保存使用同文件系统暂存及替换，失败回滚；图片硬链接只用于已有工作空间副本的短期暂存，初次导入始终实际复制原文件。

保存后的回收站可跨重启恢复；未保存的筛选修改在关闭/换项目时提供保存、放弃、取消。切换工作空间不会移动已打开项目的位置。未进行真实大规模数据集压测、断电恢复或 GPU 新验证；本次未改变训练后端。
