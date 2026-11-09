# Project Naming Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans, sequentially. Repository single-agent convention and user authorization govern execution.

**Goal:** 将当前产品的代码包、入口、构建信息与可见品牌统一为 YOLO-BACKPROP，兼容已有标注、插件和配置。

**Architecture:** 迁移 ISAT/ 为 yolo_backprop/；包元数据统一产品名称，旧插件导入使用模块别名；文件格式保持原样。

**Tech Stack:** Python / PyQt5 / unittest / setuptools.

**Spec:** docs/superpowers/specs/2026-11-05-project-naming-design.md

## Global Constraints

- 单代理，保留已有未提交改动；不提交／推送／发布。
- 原作者、许可证、第三方组件和历史记录保留，不重写旧项目。
- 迁移个人配置须逐字节一致；版本数值仍为 1.5.2。

## Review Focus

- 动态导入、Hydra 目标和工具子进程不能仍指向旧主包。
- 旧插件不得加载另一套 Qt 类／枚举；新旧插件组避免重复加载。
- 原桌面入口和旧环境变量仍可启动；现有模型设置不丢失。
- 打包数据和资源均跟随新目录，避免漏掉模型配置或个人文件误入发布包。
- 主窗口、关于窗口、帮助入口和当前 README 不再误导到上游软件。

## Task 1: 主包与启动／配置兼容

Files: yolo_backprop/（迁移 ISAT/）、run-yolo-backprop.sh、run-isat.sh、setup-model-runtime.sh、main.py、tests/。
Interfaces: 新主包及旧 ISAT 模块别名指向同一对象；YOLO_BACKPROP_PYTHON / YOLO_BACKPROP_MODEL_DATA_DIR 优先，旧变量兼容。

- [x] 新增启动脚本、旧插件单例导入、模型数据目录与配置保留的失败测试。
- [x] 迁移目录与内部导入／模型路径，增加兼容层，重命名根类别配置。
- [x] 运行命名、桌面入口及现有筛选／工作台回归，核对个人文件哈希。

## Task 2: 品牌、构建与文档

Files: setup.py、MANIFEST.in、build_exe.*、docker/、yolo_backprop/widgets/about_dialog.py、mainwindow.py、desktop.py、README*、docs/source/、NOTICE。
Interfaces: 发行包 yolo-backprop，命令 yolo-backprop，关于窗口显示本项目名称／仓库并保留上游署名。

- [x] 新增元数据、关于窗口和更新来源的测试并确认失败。
- [x] 更新构建与文案，保留上游来源说明和旧格式名称；当前文档使用新导入与启动方式。
- [x] 全量 unittest、构建清单／语法检查、实际窗口与关于窗口截图、自审剩余旧名称；记录结果。

## 执行记录

- 当前 224 项测试通过作为已验证基线。当前桌面入口引用 run-isat.sh，保留转发脚本保证改名后继续可用。
- 已确认安装的 AutoAnnotatePlugin 使用 ISAT.widgets.plugin_base / polygon 和 ISAT.__version__；兼容层必须复用 canonical 模块。
- Ruling: 按现有 YOLO-BACKPROP 品牌命名，无需重新选择产品名；本次不改 Git 分支名、用户 Python 环境名或历史来源记录。
- Task 1 / Task 2 complete。首轮新命名 6 项用例出现 2 个断言失败和 4 个新包尚不存在的导入错误；迁移后修复格式类 ISAT.ANNO 被误识别为包名的引用。目标回归 86 项通过。新增插件组去重、无发布时静默、SAM2 动态目标验证后全量 233 项通过。
- 自审修正：同步主题控件选择器；关于窗口 retranslateUi 先加入失败断言，防止重新翻译恢复上游项目链接；源码打包排除个人 software.yaml 与字节码，包含新启动脚本和模型配置。最终全量 233 项通过（43.469s）。
- 实际验证：5 张窗口截图已检查；源码包从独立临时目录启动筛选／标注／模型开发成功，安装的旧自动标注插件正常加载。个人 software.yaml 与原 isat.yaml（现 categories.yaml）的 SHA-256 均未改变。未发布、未运行 Windows／Docker 构建；旧桌面入口经转发脚本仍可启动。
