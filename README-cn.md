> **YOLO-BACKPROP：基于 ISAT 的标注与神经网络训练工作台**
>
> 代码仓库：[YOLO-LAB-GUI](https://github.com/Liujingze11/YOLO-LAB-GUI)，当前原生工作台分支为 `feature/isat-model-development`。本地开发目录已统一为 `YOLO-LAB-GUI`；原 GUI / Electron 开发目录保留在历史归档中。
>
> 以原版 ISAT 为主体，左侧提供“数据筛选 / 数据标注 / 模型开发”导航。原标注界面继续保留；模型开发包含训练、推理、模型导出、日志结果、工具和设置。可从当前已保存标注生成独立 YOLO 数据集并直接用于训练。
>
> **玻璃外观**：首页、筛选、标注及模型开发统一使用灰白底色、黑灰文字、半透明面板、圆角和少量蓝色选中态。侧栏保留返回首页和三个功能入口，移除重复的“工作空间”。现有按钮区域和功能保留，模型页仍可切换深色。[界面与验证](docs/superpowers/verification/2026-11-02-neutral-glass/README.md)。
>
> **启动首页**：打开软件先显示同尺寸的“新建项目”“打开项目”和最近项目卡片。新建默认命名“新项目”，重名自动顺延，可修改；留空也使用可用默认名称，按回车创建独立子文件夹并进入工作台。手动输入非法或已占用名称时不可创建。[创建验证](docs/superpowers/verification/2026-11-02-create-enter-default/README.md)。打开不要求完整结构或本软件标记：有可读取图片的文件夹即可进入筛选，已有 ISAT 图片/JSON 会校验并读取，有效 YOLO 数据配置会接入模型开发。外部原目录保持不变，状态、筛选副本及默认输出另存；后续打开恢复工作副本和训练草稿。右键支持打开、打开文件夹、复制路径、从列表移除和删除。“从列表移除”保留文件；只有能验证由软件新建的项目目录才允许确认后移入系统回收站，外部目录不能整目录删除。桌面、主目录等位置受保护。后台任务和未保存内容保留切换守卫，来源消失或同路径目录被替换时不会重建原目录或混入旧记录。[最低标准与验证](docs/superpowers/verification/2026-11-02-flexible-projects/README.md)。
>
> **数据筛选与工作空间**：进入工作空间后拖入图片文件夹（包含子目录），图片及有效 ISAT JSON 会复制到独立项目。点击“返回首页”可切换或打开项目。项目包含 `images/`、`json/` 和隐藏回收站；JSON 在保存标注后生成，不预造空标注。图片右键提供重命名和移入回收站，顶部不再重复显示这些按钮或工作空间说明。左侧底部回收站单行展示照片，双击恢复单张，支持多选恢复。[本次布局验证](docs/superpowers/verification/2026-11-02-screening-trash-strip/README.md)。Delete 先移入可恢复的回收站；“保存筛选”成功后询问是否永久删除这些副本，选择保留则下次打开仍可恢复。原始图片和原始 JSON 不会被重命名或删除。“导入数据标注”保存当前筛选并打开原生画布；同一项目已有未保存标注时，需先保存标注。Ctrl+S 保存筛选，Ctrl+Shift+T 打开回收站。[筛选界面与验证](docs/superpowers/verification/2026-10-30-screening-workspaces/README.md)。
>
> **浏览操作**：左侧固定三列。拖到主图上替换，单图右边缘的提示区加入对比；双图左右分别接收替换，等分右侧。预览图可左键拖回左栏移出预览，缩略图不会重复或删除；中键平移、滚轮缩放。C 打开可拖入的对比区，Esc 退出，左右箭头切图、F 适应窗口、F2 重命名。右键提供常用操作；“快捷键…”可修改、清空、恢复默认和保存快捷键，重启后保留。
>
> 启动：`./run-isat.sh`。如已有环境缺少少量启动依赖，先执行 `./setup-model-runtime.sh`（仅安装到本项目 `.runtime/python`）；可用 `ISAT_PYTHON=/absolute/path/to/python ./run-isat.sh` 选择解释器。模型开发需要 Python 3.10+、PyQt5、Ultralytics 和 Matplotlib；完整首次安装可使用项目的 `[yolo]` 可选依赖。模型缓存路径设置在下次启动生效。
>
> 本机 CPU 训练、推理及 ONNX / ONNX Runtime 已验证；GPU 和其他导出后端的实际支持见 [验证记录](docs/superpowers/verification/2026-10-30-isat/README.md)。
>
> Linux 应用菜单：在当前 Python 环境运行 `python -m ISAT.desktop`，或使用软件菜单中的“创建桌面快捷方式”。“显示应用”中搜索 **YOLO** 或 **BACKPROP**，点击 **YOLO-BACKPROP** 即可启动本源码版本。安装会更新原 `ISAT.desktop` 入口，旧入口备份到 `~/.local/state/isat-yolo/launcher-backups/`；移动源码目录后需重新安装入口。

<h1 align='center'>ISAT_with_segment_anything [isat-sam]</h1>
<h2 align='center'>一款基于SAM的交互式半自动图像分割标注工具</h2>
<p align='center'>
    <a href='https://github.com/yatengLG/ISAT_with_segment_anything/stargazers' target="_blank"><img alt="GitHub forks" src="https://img.shields.io/github/stars/yatengLG/ISAT_with_segment_anything"></a>
    <a href='https://github.com/yatengLG/ISAT_with_segment_anything/forks' target="_blank"><img alt="GitHub forks" src="https://img.shields.io/github/forks/yatengLG/ISAT_with_segment_anything"></a>
    <a href='https://pypi.org/project/isat-sam/' target="_blank"><img alt="PyPI - Version" src="https://img.shields.io/pypi/v/isat-sam?style=social&logo=pypi"></a>
    <a href='https://pypi.org/project/isat-sam/' target="_blank"><img alt="Pepy Total Downlods" src="https://img.shields.io/pepy/dt/isat-sam?style=social&logo=pypi"></a>
</p>
<p align='center'>
<b>⭐️ 如果你觉得这个项目有用，欢迎点个 Star 支持一下！ ⭐️</b>
</p>
<p align='center'>
    <a href='README-cn.md'><b>[中文]</b></a>
    <a href='README.md'><b>[English]</b></a>
</p>
<p align='center'><img src="./display/software.gif" alt="software.gif"></p>

专注于图像分割领域，我们致力于打造最好的图像分割标注软件。

请查阅我们最新的[中文文档](https://isat-sam.readthedocs.io/zh-cn/latest/) 或 [Documentation in English](https://isat-sam.readthedocs.io/en/latest/#)

---

# 更新
- **V1.5.2版本，支持基于sam3的视觉提示（visual prompt）功能**
    <details>
        <summary>视觉提示</summary>
            <p align='center'><img src="./display/visual_prompt.gif" alt="visual_prompt.gif"></p>
    </details>

- **V1.5.0版本，支持SAM3模型，并添加了文本提示（text prompt）功能**

    <details>
        <summary>文本提示</summary>
            <h3>单类别</h3>
                <p align='center'><img src="./display/text_prompt1.gif" alt="text_prompt1.gif"></p>
            <h3>多类别</h3>
                <p align='center'><img src="./display/text_prompt2.gif" alt="text_prompt2.gif"></p>
    </details>

- **V1.4.0版本添加了插件系统。** 可以使用较少量的代码，扩展ISAT的功能。
  
    以下是一些插件示例:
  - [ISAT_plugin_auto_annotate](https://github.com/yatengLG/ISAT_plugin_auto_annotate) ![PyPI - Version](https://img.shields.io/pypi/v/isat-plugin-auto-annotate?style=social&logo=pypi)
 ![Pepy Total Downloads](https://img.shields.io/pepy/dt/isat-plugin-auto-annotate?style=social) : 仅用240行代码实现的**自动标注**功能（使用yolo模型）。
  - [ISAT_plugin_mask_export](https://github.com/yatengLG/ISAT_plugin_mask_export) ![PyPI - Version](https://img.shields.io/pypi/v/isat-plugin-mask-export?style=social&logo=pypi)
![Pepy Total Downloads](https://img.shields.io/pepy/dt/isat-plugin-mask-export?style=social) : 仅用160行代码实现的**mask导出**功能。

- 其他版本以及更新日志，请查阅[发布页](https://github.com/yatengLG/ISAT_with_segment_anything/releases)

# 安装

- 新建conda环境（推荐，可选）
    ```shell
    # 创建环境
    conda create -n isat_env python=3.8
    
    # 激活环境
    conda activate isat_env
    ```

- 安装
    ```shell
    pip install isat-sam
    ```

- 运行
    ```shell
    isat-sam
    ```

# Star History

**请给该项目一个star，您的点赞就是对我最大的支持与鼓励**
[![Star History Chart](https://api.star-history.com/svg?repos=yatengLG/ISAT_with_segment_anything&type=Date)](https://star-history.com/#yatengLG/ISAT_with_segment_anything&Date)


# 核心贡献者

<table border="0">
<tr>
    <td><img alt="yatengLG" src="https://avatars.githubusercontent.com/u/31759824?v=4" width="60" height="60" href="">
    <td><img alt="Alias-z" src="https://avatars.githubusercontent.com/u/66273343?v=4" width="60" height="60" href="">
    <td>...
</td>
</tr>
<tr>
  <td><a href="https://github.com/yatengLG">yatengLG</a>
  <td><a href="https://github.com/Alias-z">Alias-z</a>
    <td><a href="https://github.com/yatengLG/ISAT_with_segment_anything/graphs/contributors">...</a>
</tr>
</table>


# 引用
```text
@misc{ISAT_with_segment_anything,
  title={{ISAT with Segment Anything: An Interactive Semi-Automatic Annotation Tool}},
  author={Ji, Shuwei and Zhang, Hongyuan},
  url={https://github.com/yatengLG/ISAT_with_segment_anything},
  note={Updated on 2025-02-07},
  year={2024},
  version={1.33}
}
```
