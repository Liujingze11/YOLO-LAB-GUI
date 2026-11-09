# YOLO-BACKPROP 命名迁移验证

## 完成内容

- 主包 `ISAT/` 迁移为 `yolo_backprop/`，内部导入、工具进程、SAM2 Hydra 配置及资源路径跟随迁移；旧主包目录不再存在。
- 主启动脚本 `run-yolo-backprop.sh`；安装包／控制台命令 `yolo-backprop`；默认类别配置 `categories.yaml`。仓库仍为 YOLO-LAB-GUI，版本数值保持 1.5.2。
- 关于窗口、构建脚本、Linux／Windows 入口生成、IDE 模块、当前文档及项目链接采用当前品牌；更新检查只查询本仓库发布页。原 README 单独归档，保留原作者、许可及 NOTICE。
- 旧 `run-isat.sh` 转发新入口；旧解释器／模型配置变量仍兼容。旧模型数据目录存在时继续复用。旧插件的 ISAT 导入映射到同一 canonical 模块，避免类和枚举重复；新旧插件组去重加载。
- 保留 ISAT JSON description、isat.yaml、格式转换接口、外部后端／插件名称、模型下载来源、原作者标识和历史记录；本次不改动已有项目中的文件。

## 验证结果

- 首轮新增 6 项测试确认旧入口／旧包名／旧元数据不满足新命名。迁移后目标回归 86 项通过；最终增加到 **233 项全量测试，全部通过（43.469s）**。
- 覆盖插件导入对象身份、新旧启动入口和解释器优先级、模型配置路径兼容、发布包元数据、关于窗口及再次翻译、更新来源及无发布处理、新旧插件组去重、SAM2 配置解析和模型类解析。
- 自审发现的格式类 `ISAT.ANNO` 引用保留为格式 API；主题选择器同步迁移；关于窗口再次翻译的失败测试修复后通过。
- 实际安装的 AutoAnnotatePlugin 在完整工作台和独立源码包中均加载成功。
- 398 个 Python 文件通过语法解析，四个 shell 入口通过 bash -n；git diff --check 通过。
- 个人 software.yaml 和原 isat.yaml（现 categories.yaml）迁移前后 SHA-256 完全一致；前者继续忽略，不加入发行包。
- setuptools sdist 构建成功。检查归档包含 canonical 包、8 个 SAM2 YAML、类别配置、翻译、图标及新入口；不含旧 ISAT 主包、个人软件设置或 Python 字节码。
- 从独立临时目录解包启动真实 MainWindow，依次打开筛选／标注／模型开发并加载旧插件，退出码为 0。没有依赖工作区源码路径兜底。
- 未发布或上传软件；Windows 可执行文件和 Docker 构建仅更新配置，本环境未构建验证。当前桌面快捷方式仍通过旧脚本转发；新安装入口使用新脚本。

```bash
QT_QPA_PLATFORM=offscreen MPLCONFIGDIR=/tmp/yolo-naming-final-mpl PYTHONPATH=.runtime/python:. /home/ljz/miniconda3/envs/isat_env/bin/python -m unittest discover -s tests -v
PYTHONPATH=.runtime/python:. /home/ljz/miniconda3/envs/isat_env/bin/python setup.py sdist --dist-dir /tmp/yolo-naming-dist
```

日志：`/tmp/yolo-naming-final.log`、`/tmp/yolo-naming-package-final.log`、`/tmp/yolo-naming-archive-smoke.log`。

## 界面检查

真实 Qt 控件离屏截图，已逐张检查：

- [项目首页](01-home.png)
- [数据筛选](02-screening.png)
- [数据标注](03-annotation.png)
- [模型开发](04-model-development.png)
- [关于窗口](05-about.png)
