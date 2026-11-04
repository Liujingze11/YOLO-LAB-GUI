# 数据筛选实施计划

Spec: `docs/superpowers/specs/2026-10-30-data-screening.md`

执行：当前 `feature/isat-model-development` 分支，单代理顺序实施；用户要求增加功能，继续完成，无新 worktree 或代理。默认仅编辑筛选结果，保留原文件。

## 全局约束

原生 PyQt5、现有运行环境、不安装新依赖。保留现有软件配置及启动器改动。不推送、不重建远程仓库。后台复制、可取消、无覆盖、不生成伪负样本 JSON。

## Task 1 — 筛选记录与项目复制

Create `ISAT/data_screening/{__init__,session}.py`，test `tests/data_screening/test_session.py`。

接口：`ScreeningSession.scan(root, check_cancelled, progress)` 返回含 `items` 和 `skipped` 的记录；`rename(item, stem)`、`remove(items)` 改记录；`export_project(destination, check_cancelled, progress, categories)` 返回 `project_root/image_root/label_root/files`。每条记录含 source/name/width/height/annotation。

1. 写测试，覆盖递归与损坏文件、同 stem 去重、中文重命名、移除后原图不变、已有标注保持和重命名、无标注不生成 JSON、取消回滚和拒绝覆盖。
2. 运行并确认因尚未实现失败。
3. 实现扫描、校验与原子项目复制。
4. 运行该测试与既有套件。

## Task 2 — 原生筛选页面

Create `ISAT/data_screening/{workers,widget}.py`，test `tests/data_screening/test_widget.py`。

接口：`DataScreeningWidget.project_ready(dict)`，`before_import` 回调，`active_workers()` / `stop_workers()`；公开 `open_folder(path)`、`session`、网格 `grid`。线程传递 QImage，在 GUI 线程创建 QPixmap。展示删除与重命名仅作用于筛选结果。

1. 写真实拖放、后台扫描与预览、选择删除/重命名和导入按钮输出测试，运行确认失败。
2. 实现网格/预览、后台扫描与复制、取消、快捷键作用域、输出位置选择。
3. 运行页面测试，检查 1280×900 截图。

## Task 3 — 导航和标注衔接

Modify `ISAT/model_development/integration.py`，test `tests/model_development/test_integration.py`；更新 README 和验证记录。

接口：`show_screening()` 切页且保留画布；`open_screened_project(result)` 验证空闲与未保存状态后更新原生 ISAT 的图片/JSON 根目录并显示首图。扫描/复制/预览线程纳入关闭清理。

1. 写三页切换、隐藏快捷键、真实导入并保存 JSON、未保存取消不切换测试，确认失败。
2. 实现导航复用和导入，不更换原生画布。
3. 运行完整 `unittest discover -s tests -v`、真实截图和源码启动检查；自审文件覆盖、关闭线程、标注状态。记录结果，保留用户配置字节。

## Review Focus

- 多目录重名和大小写 stem 冲突：一图一 JSON，测试 Task 1。
- 源文件被外部删除或修改：复制失败不发布半成品，测试 Task 1。
- 异步预览结果晚于选择变化：不显示旧图片，测试 Task 2。
- 三页互切时快捷键和画布恢复：测试 Task 3。
- 导入时取消未保存标注，或后台线程仍运行：保留当前数据，测试 Task 3。
