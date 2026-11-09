# YOLO-BACKPROP

> **YOLO-BACKPROP：基于 ISAT 的标注与神经网络训练工作台**
>
> 代码仓库：[YOLO-LAB-GUI](https://github.com/Liujingze11/YOLO-LAB-GUI)，当前原生工作台统一在唯一维护的 `main` 分支开发。本地开发目录已统一为 `YOLO-LAB-GUI`；原 GUI / Electron 开发目录保留在历史归档中。
>
> 原生 PyQt5 工作台左侧提供“数据筛选 / 数据标注 / 模型开发”导航。标注界面基于 ISAT 扩展；模型开发包含训练、推理、模型导出、日志结果、工具和设置。可从当前已保存标注生成独立 YOLO 数据集并直接用于训练。
>
> **玻璃外观**：首页、筛选、标注及模型开发统一使用灰白底色、黑灰文字、半透明面板、圆角和少量蓝色选中态。侧栏保留返回首页和三个功能入口，移除重复的“工作空间”。现有按钮区域和功能保留，模型页仍可切换深色。[界面与验证](docs/superpowers/verification/2026-11-02-neutral-glass/README.md)。
>
> **启动首页**：顶部提供“打开项目”和“新建项目”按钮，下方仅展示最近项目；卡片显示封面、项目类型、路径及最近打开时间。新建弹窗同时填写名称和保存位置，记住上次成功创建的位置，并预览最终目录。默认名“新项目”支持重名顺延，回车创建，非法或已占用名称不可提交。打开时在后台自动识别已有项目、图片、ISAT 标注和 YOLO 数据集，支持取消。图片和有效 ISAT JSON 整理到独立筛选副本；YOLO 图片与标签复制到独立数据集，保留 train/val/test、类别编号及未标注状态，同名文件自动配套改名，并生成相对路径配置接入模型开发。可识别自定义名称的 YOLO YAML；多个候选配置、无类别配置的 YOLO 标签或无效标注明确报错。原目录保持不变，重开复用工作副本与训练草稿，不覆盖副本中的修改。右键保留打开、打开文件夹、复制路径、从列表移除和删除；仅可验证由软件创建的项目可确认后移入系统回收站。后台任务、未保存内容和来源目录身份变化仍有切换守卫。[界面与验证](docs/superpowers/verification/2026-11-05-project-home/README.md)。
>
> **数据筛选与工作空间**：进入工作空间后拖入图片文件夹（包含子目录），图片及有效 ISAT JSON 会复制到独立项目。点击“返回首页”可切换或打开项目。项目包含 `images/`、`json/` 和隐藏回收站；JSON 在保存标注后生成，不预造空标注。图片右键提供重命名和移入回收站，顶部不再重复显示这些按钮或工作空间说明。左侧底部回收站单行展示照片，双击恢复单张，支持多选恢复。[本次布局验证](docs/superpowers/verification/2026-11-02-screening-trash-strip/README.md)。Delete 先移入可恢复的回收站；“保存筛选”成功后询问是否永久删除这些副本，选择保留则下次打开仍可恢复。原始图片和原始 JSON 不会被重命名或删除。未导入时仅显示居中的“打开图片文件夹”按钮及拖入提示；导入后展开约 30/70 的缩略图与预览两栏，打开按钮位于列表顶部，翻页、图片序号和适应窗口集中在预览底部。空回收站折叠为一行，移除图片后自动展开，也可手动收起；恢复到零时再次折叠。进度与取消操作位于底部任务行。同一项目已有未保存标注时，需先保存标注。Ctrl+S 保存筛选，Ctrl+Shift+T 打开回收站。[筛选界面与验证](docs/superpowers/verification/2026-10-30-screening-workspaces/README.md)。
>
> **筛选交互**：图片区和回收站都支持从空白处框选、Ctrl+单击增减多选、Shift+单击连续选择、Ctrl+A 全选。拖动任一已选缩略图可整组移入回收站或拖回恢复；折叠的回收站标题栏也可接收拖入。对比时点击哪一侧，方向键与底部翻页／序号就控制哪一侧，另一侧保持不变，蓝色细边框标明当前侧；翻页跳过另一侧已显示图片。底部不再显示“退出对比”按钮，Esc 与右键退出仍可用。[交互验证](docs/superpowers/verification/2026-11-05-screening-interactions/README.md)。

> **浏览操作**：左侧固定三列。单图中央接收替换，左右边缘均可加入对比：拖左侧新图在左，拖右侧新图在右，原图保留在另一侧；双图等宽，各侧可独立替换。两张预览图可互拖换位，保留各自缩放和平移位置。项目预览图可直接拖入回收站，回收站单图拖入预览时自动恢复；落点提前提示对比方向、互换、替换或恢复。预览图可左键拖回左栏移出预览，缩略图不会重复或删除；中键平移、滚轮缩放。C 打开可拖入的对比区，Esc 退出，左右箭头切图、F 适应窗口、F2 重命名。右键提供常用操作；标题栏左侧的“快捷键”入口在所有页面可用，统一窗口按“数据筛选 / 数据标注 / 模型开发”分页。可修改、清空、恢复当前页默认，并分别保存各页；重启后保留。原筛选右键菜单和标注菜单也打开同一窗口。同页重复绑定会提示冲突，标注数字 0–9 保留给类别选择。
>
> 启动：`./run-yolo-backprop.sh`。如已有环境缺少少量启动依赖，先执行 `./setup-model-runtime.sh`（仅安装到本项目 `.runtime/python`）；可用 `YOLO_BACKPROP_PYTHON=/absolute/path/to/python ./run-yolo-backprop.sh` 选择解释器。模型开发需要 Python 3.10+、PyQt5、Ultralytics 和 Matplotlib；完整首次安装可使用项目的 `[yolo]` 可选依赖。模型缓存路径设置在下次启动生效。
>
> 本机 CPU 训练、推理及 ONNX / ONNX Runtime 已验证；GPU 和其他导出后端的实际支持见 [验证记录](docs/superpowers/verification/2026-10-30-isat/README.md)。
>
> Linux 应用菜单：在当前 Python 环境运行 `python -m yolo_backprop.desktop`，或使用软件菜单中的“创建桌面快捷方式”。“显示应用”中搜索 **YOLO** 或 **BACKPROP**，点击 **YOLO-BACKPROP** 即可启动本源码版本。安装使用独立的 `yolo-backprop.desktop` 入口，替换此前 YOLO-BACKPROP 使用的 `ISAT.desktop`，旧入口备份到 `~/.local/state/yolo-backprop/launcher-backups/`；移动源码目录后需重新安装入口。

标题栏将快捷键、居中项目名和窗口按钮合为一行，支持明暗主题、长标题提示，并保留已有关闭保护。[验证记录](docs/superpowers/verification/2026-11-09-title-bar/README.md)。

## 开发与运行

```bash
# 在 Python 3.10+ 环境中安装本地源码和模型开发依赖
python -m pip install -e '.[yolo]'
./run-yolo-backprop.sh
# 安装后的命令：yolo-backprop
```

应用名为 **YOLO-BACKPROP**，仓库为 **YOLO-LAB-GUI**，Python 主包为 `yolo_backprop`。当前版本值仍为 1.5.2；本次命名迁移没有发布新版本。

`run-isat.sh` 和 `ISAT_PYTHON` 仅保留为旧入口兼容。默认类别配置为 `yolo_backprop/categories.yaml`；个人软件设置原样保留。模型设置优先使用 `YOLO_BACKPROP_MODEL_DATA_DIR`，兼容旧变量及旧数据目录。旧标注的 ISAT JSON / isat.yaml 和已安装插件继续可用。

## 来源

本项目基于 [ISAT with Segment Anything](https://github.com/yatengLG/ISAT_with_segment_anything)，保留原作者与第三方许可。详见 [NOTICE](NOTICE)、[LICENSE](LICENSE) 和 [上游说明归档](docs/upstream/README-cn.md)。模型开发模块的移植来源记录在 [PROVENANCE.json](yolo_backprop/model_development/PROVENANCE.json)。
