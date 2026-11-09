# 项目首页与自动识别整理验证（2026-11-05）

- 首页顶部为“打开项目／新建项目”，最近项目区域仅显示实际项目。卡片包含封面、路径、类型/图片数、最近打开时间；悬停可查看来源与工作副本路径。
- 新建弹窗合并名称和位置；可直接编辑或浏览位置，预览最终目录，记住成功创建的位置。回车创建、默认名称、重名校验、取消浏览和取消创建均验证。
- 后台识别已有项目、图片、ISAT 标注及 YOLO 配置。识别与 YOLO 整理可取消，取消等待临时文件清理完成。
- 图片/ISAT 复用筛选副本导入。YOLO 整理为独立 `dataset/images/<split>`、`dataset/labels/<split>` 和相对路径 `data.yaml`，保留 train/val/test、类别编号与未标注状态。同名图片配套改名，原目录文件字节不变。
- 重开复用已有副本，不覆盖其中修改。自定义 YAML 名称可识别；多个配置、缺失类别配置、无效标签及符号链接明确拒绝，不猜测。
- 复查修复异常历史时间导致的首页崩溃、间接符号链接与悬空标签被误认为无标注的问题。

## 验证结果

运行环境：现有 `isat_env`，`QT_QPA_PLATFORM=offscreen`，`PYTHONPATH=.runtime/python:.`。

```bash
QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/yolo-matplotlib-final PYTHONPATH=.runtime/python:. \
  /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest discover -s tests
```

最终结果：177 项测试通过，0 失败，耗时 34.452 秒；`git diff --check` 通过。

覆盖：原目录保持不变、类别字典乱序、TXT 图片清单、同名文件配对、缺少标签、取消与临时目录清理、复制时源文件变化、重开复用、后台任务/未保存内容切换守卫，以及现有筛选和标注流程。

界面截图由实际 PyQt 窗口离屏渲染并逐张检查。测试使用临时项目与配置，不改动个人设置；原生系统文件选择器的人工交互未在本轮验证。

## 截图

- [最近项目首页](home.png)
- [空首页](home-empty.png)
- [800px 窄窗口](home-narrow.png)
- [新建项目弹窗](create-project.png)
- [自动识别整理后的项目](home-recognized.png)
