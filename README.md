> **YOLO-BACKPROP: annotation and neural network training built on ISAT (2026-10-30)**
>
> **Native glass appearance:** neutral gray/white surfaces, black/gray text, translucent panels, rounded controls and restrained blue selection across the home, screening, annotation and model pages. The sidebar keeps Home and the three functional pages. Duplicate Workspace buttons are removed; project switching uses Home. Existing controls retain their areas and behavior, with the model pages still supporting dark mode. [Screenshots and verification](docs/superpowers/verification/2026-11-02-neutral-glass/README.md).
>
> **Workspace home:** equal-sized New Project, Open Project and recent cards. Create offers an editable “新项目” name with numbered alternatives when occupied; blank input also uses an available default. Press Return or keypad Enter to create an independent child folder and enter the workbench. Invalid or occupied custom names remain blocked. [Creation verification](docs/superpowers/verification/2026-11-02-create-enter-default/README.md). Open recognizes readable image folders without requiring a complete structure or application marker; existing ISAT images/JSON are validated and copied into screening, while valid YOLO data configurations open model development. External sources remain unchanged: state, screening copies and default outputs use an independent workspace. Reopening restores copies and training drafts. External folders can be removed from the list but cannot be deleted as directories. Verified application-created projects retain confirmed system-trash deletion. Desktop and other common locations remain protected. Task and unsaved-work guards remain in place; missing or replaced source directories cannot recreate originals or inherit unrelated work. [Minimum formats and verification](docs/superpowers/verification/2026-11-02-flexible-projects/README.md).
>
> Original ISAT remains the main application. A native sidebar switches between data screening, annotation and six PyQt5 development pages: training, inference, export, logs/results, dataset tools and settings. Saved ISAT annotations can be prepared as a separate YOLO dataset and passed directly to training.
>
> **Screening workspaces**: choose a location from the sidebar's Workspace entry, then drop an image folder (including subfolders). Images and valid existing ISAT JSON are copied into an independent project containing `images/`, `json/`, a hidden trash directory and a project manifest. The last workspace is remembered; saved projects can be reopened. Delete stages images in recoverable trash. After a successful save, confirm whether to permanently remove those copies; keeping them allows restoration after restarting. Original images and labels are never renamed or deleted. Import saves the selection and opens the original annotation canvas. Save any pending annotations before saving screening changes to the same project. No empty annotation files are invented. Ctrl+S saves screening; Ctrl+Shift+T opens trash. See [current screenshots and verification](docs/superpowers/verification/2026-10-30-screening-workspaces/README.md).
>
> **Viewer controls**: thumbnails stay in three columns. Drop onto the main image to replace it, or onto its right edge to add an equal-width comparison. Each side can then be replaced independently. Left-drag a preview back to the thumbnail grid to remove it from the viewer without deleting or duplicating its thumbnail. Use the middle button to pan and the wheel to zoom. C opens a comparison drop area, Esc exits it, Left/Right navigates, F fits, and F2 renames. The context menu provides common operations; the **快捷键…** button edits, disables, resets and saves shortcuts across restarts.
>
> Run `./run-isat.sh`. If the existing environment misses small startup dependencies, run `./setup-model-runtime.sh`; it installs only into this project's `.runtime/python` overlay. Select an interpreter with `ISAT_PYTHON=/absolute/path/to/python ./run-isat.sh`. Model development requires Python 3.10+, PyQt5, Ultralytics and Matplotlib; a fresh installation can use the `[yolo]` extra. Custom model-cache paths take effect on the next launch.
>
> CPU training, inference and ONNX export/runtime have been tested. See [verification and limits](docs/superpowers/verification/2026-10-30-isat/README.md) for GPU and optional export backends. No remote repository was created or pushed.
>
> Linux application menu: run `python -m ISAT.desktop` in the current Python environment, or use the application's “Create desktop shortcut” menu action. Search **YOLO** or **BACKPROP** in Show Applications and launch **YOLO-BACKPROP**. This updates `ISAT.desktop`, backs up the previous entry under `~/.local/state/isat-yolo/launcher-backups/`, and starts this source checkout. Reinstall the entry after moving the checkout.

<h1 align='center'>ISAT_with_segment_anything [isat-sam]</h1>
<h2 align='center'>An Interactive Semi-Automatic Annotation Tool Based on Segment Anything</h2>
<p align='center'>
    <a href='https://github.com/yatengLG/ISAT_with_segment_anything/stargazers' target="_blank"><img alt="GitHub forks" src="https://img.shields.io/github/stars/yatengLG/ISAT_with_segment_anything?style=social"></a>
    <a href='https://github.com/yatengLG/ISAT_with_segment_anything/forks' target="_blank"><img alt="GitHub forks" src="https://img.shields.io/github/forks/yatengLG/ISAT_with_segment_anything"></a>
    <a href='https://pypi.org/project/isat-sam/' target="_blank"><img alt="PyPI - Version" src="https://img.shields.io/pypi/v/isat-sam?style=social&logo=pypi"></a>
    <a href='https://pypi.org/project/isat-sam/' target="_blank"><img alt="Pepy Total Downlods" src="https://img.shields.io/pepy/dt/isat-sam?style=social&logo=pypi"></a>
</p>
<p align='center'>
<b>⭐️ If you find this project helpful, please give it a Star! ⭐️</b>
</p>
<p align='center'>
    <a href='README-cn.md'><b>[中文]</b></a>
    <a href='README.md'><b>[English]</b></a>
</p>
<p align='center'><img src="./display/software.gif" alt="software.gif"></p>

Focusing on the field of image segmentation, we strive to create the best image segmentation annotation software.

Please refers to our latest [Documentation in English](https://isat-sam.readthedocs.io/en/latest/#) or [中文文档](https://isat-sam.readthedocs.io/zh-cn/latest/)

---

# News
- **In version 1.5.2, ISAT supports visual prompt base on SAM3.**
    
    <details>
        <summary>Visual prompt</summary>
            <p align='center'><img src="./display/visual_prompt.gif" alt="visual_prompt.gif"></p>
    </details>

- **In version 1.5.0, ISAT supports SAM3 and also supports text prompt.**
    
    <details>
        <summary>Text prompt</summary>
            <h3>For single category</h3>
                <p align='center'><img src="./display/text_prompt1.gif" alt="text_prompt1.gif"></p>
            <h3>For multiple categories</h3>
                <p align='center'><img src="./display/text_prompt2.gif" alt="text_prompt2.gif"></p>
    </details>

- **In version 1.4.0, ISAT add a plugin system.** You can use a small amount of code to extend the functionality of ISAT.
  
    Here are some official plugin examples:
  - [ISAT_plugin_auto_annotate](https://github.com/yatengLG/ISAT_plugin_auto_annotate) ![PyPI - Version](https://img.shields.io/pypi/v/isat-plugin-auto-annotate?style=social&logo=pypi)
 ![Pepy Total Downloads](https://img.shields.io/pepy/dt/isat-plugin-auto-annotate?style=social) : An auto-annotation function based on the YOLO model, implemented with just 240 lines of code.
  - [ISAT_plugin_mask_export](https://github.com/yatengLG/ISAT_plugin_mask_export) ![PyPI - Version](https://img.shields.io/pypi/v/isat-plugin-mask-export?style=social&logo=pypi)
![Pepy Total Downloads](https://img.shields.io/pepy/dt/isat-plugin-mask-export?style=social) : A mask export function, implemented with just 160 lines of code.

- For other versions and the release note, please refer to [releases](https://github.com/yatengLG/ISAT_with_segment_anything/releases)

# Install

- Create a conda environment(recommended, optional)
    ```shell
    # create environment
    conda create -n isat_env python=3.8
    
    # activate environment
    conda activate isat_env
    ```

- Install
    ```shell
    pip install isat-sam
    ```

- Run
    ```shell
    isat-sam
    ```

# Star History

**Please support us with a star—it's like a virtual coffee!**
[![Star History Chart](https://api.star-history.com/svg?repos=yatengLG/ISAT_with_segment_anything&type=Date)](https://star-history.com/#yatengLG/ISAT_with_segment_anything&Date)


# Contributors

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


# Citation
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
