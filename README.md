# YOLO-BACKPROP

> **YOLO-BACKPROP: annotation and neural network training built on ISAT**
>
> Repository: [YOLO-LAB-GUI](https://github.com/Liujingze11/YOLO-LAB-GUI). The native workbench is developed directly on `main`, the only maintained branch; the local checkout is named `YOLO-LAB-GUI`. The previous GUI / Electron checkout is preserved in the local history archive.
>
> **Native glass appearance:** neutral gray/white surfaces, black/gray text, translucent panels, rounded controls and restrained blue selection across the home, screening, annotation and model pages. The sidebar keeps Home and the three functional pages. Duplicate Workspace buttons are removed; project switching uses Home. Existing controls retain their areas and behavior, with the model pages still supporting dark mode. [Screenshots and verification](docs/superpowers/verification/2026-11-02-neutral-glass/README.md).
>
> **Workspace home:** Open Project and New Project are header buttons; the gallery contains only recent projects with covers, source types, paths and last-opened times. The combined creation dialog edits the name and location, previews the destination and remembers the last successful location. Opening recognizes existing workspaces, image folders, ISAT annotations and YOLO datasets in a cancelable background operation. Images and ISAT JSON use independent screening copies. YOLO images and labels are organized into a private dataset preserving train/val/test, class indices and unlabelled images; colliding names are paired and renamed, and a relative-path YAML opens in model development. Custom YOLO YAML names are supported; ambiguous configurations, missing class metadata and invalid labels are reported. Original sources stay unchanged and reopening reuses edited working copies and training drafts. Task, unsaved-work and source-identity guards remain in place. Context menus retain open, reveal, copy path and remove; only verified application-created projects can be moved to system trash after confirmation. [Screenshots and verification](docs/superpowers/verification/2026-11-05-project-home/README.md).
>
> The workbench uses native PyQt5. A native sidebar switches between data screening, annotation and six PyQt5 development pages: training, inference, export, logs/results, dataset tools and settings. Saved ISAT annotations can be prepared as a separate YOLO dataset and passed directly to training.
>
> **Screening workspaces**: create or open a project from Home, then drop an image folder (including subfolders). Images and valid existing ISAT JSON are copied into an independent project containing `images/`, `json/`, a hidden trash directory and a project manifest. The last workspace is remembered; saved projects can be reopened. Delete stages images in recoverable trash. After a successful save, confirm whether to permanently remove those copies; keeping them allows restoration after restarting. Original images and labels are never renamed or deleted. Before import, a centered Open Image Folder entry also accepts folder drops. Imported images reveal a roughly 30/70 thumbnail/preview layout, with Open in the list header and navigation, position and Fit below the preview. Empty trash collapses to one row; removed images expand the strip, which can also be folded manually. Progress and Cancel remain available in the bottom task area. Save any pending annotations before saving screening changes to the same project. No empty annotation files are invented. Ctrl+S saves screening; Ctrl+Shift+T opens trash. See [current screenshots and verification](docs/superpowers/verification/2026-10-30-screening-workspaces/README.md).
>
> **Screening interactions**: both thumbnail lists support rubber-band selection from empty space, Ctrl-click to toggle items, Shift-click for ranges and Ctrl+A to select all. Drag any selected thumbnail to transfer the whole selection into recoverable trash or back into the image list; the folded trash header also accepts drops. In comparison mode, click either side to direct arrow keys, navigation buttons and the position indicator to that side while keeping the other fixed. A thin blue border marks the active side, and navigation skips the image shown on the other side. The Exit Comparison button is removed; Esc and the context menu still exit. [Interaction verification](docs/superpowers/verification/2026-11-05-screening-interactions/README.md).

> **Viewer controls**: thumbnails stay in three columns. Drop onto the center of a single preview to replace it, or onto either edge to add an equal-width comparison: the new image appears on the drop side, and the original stays on the other side. Each side can then be replaced independently. Drag either preview onto the other to swap them while retaining zoom and pan, without reloading already displayed pixels. Project previews can be dragged into trash; dropping a trashed photo into a preview restores it. Drop hints show the comparison side, replacement, swapping and restoration. Left-drag a preview back to the thumbnail grid to remove it from the viewer without deleting or duplicating its thumbnail. Use the middle button to pan and the wheel to zoom. C opens a comparison drop area, Esc exits it, Left/Right navigates, F fits, and F2 renames. The context menu provides common operations; the global **快捷键** (Shortcuts) entry on the left of the title bar opens one dialog with Screening, Annotation and Model Development tabs. Each page can be edited, cleared, reset and saved independently across restarts. Existing screening and annotation menus open the same dialog. Conflicting bindings on a page are rejected; annotation digits 0–9 remain reserved for category selection.
>
> Run `./run-yolo-backprop.sh`. If the existing environment misses small startup dependencies, run `./setup-model-runtime.sh`; it installs only into this project's `.runtime/python` overlay. Select an interpreter with `YOLO_BACKPROP_PYTHON=/absolute/path/to/python ./run-yolo-backprop.sh`. Model development requires Python 3.10+, PyQt5, Ultralytics and Matplotlib; a fresh installation can use the `[yolo]` extra. Custom model-cache paths take effect on the next launch.
>
> CPU training, inference and ONNX export/runtime have been tested. See [verification and limits](docs/superpowers/verification/2026-10-30-isat/README.md) for GPU and optional export backends.
>
> Linux application menu: run `python -m yolo_backprop.desktop` in the current Python environment, or use the application's “Create desktop shortcut” menu action. Search **YOLO** or **BACKPROP** in Show Applications and launch **YOLO-BACKPROP**. This installs `yolo-backprop.desktop` with its own application identity, retires the previous YOLO-BACKPROP `ISAT.desktop` entry, backs it up under `~/.local/state/yolo-backprop/launcher-backups/`, and starts this source checkout. Reinstall the entry after moving the checkout.

The title bar combines Shortcuts, the centered project name and window controls in one row, with light/dark themes, long-name tooltips and existing close protections. [Verification](docs/superpowers/verification/2026-11-09-title-bar/README.md).

## Development and launch

```bash
# Install this checkout and model-development dependencies in Python 3.10+
python -m pip install -e '.[yolo]'
./run-yolo-backprop.sh
# Installed console command: yolo-backprop
```

The application is **YOLO-BACKPROP**, the repository is **YOLO-LAB-GUI**, and the Python package is `yolo_backprop`. The version value remains 1.5.2; this naming migration does not publish a new release.

`run-isat.sh` and `ISAT_PYTHON` remain compatibility entry points. Default categories live in `yolo_backprop/categories.yaml`; personal software settings are preserved. Model settings prefer `YOLO_BACKPROP_MODEL_DATA_DIR`, with support for the legacy variable and existing data directory. ISAT JSON / isat.yaml annotations and installed legacy plugins remain supported.

## Attribution

This project is derived from [ISAT with Segment Anything](https://github.com/yatengLG/ISAT_with_segment_anything). Original author and third-party notices remain in [NOTICE](NOTICE) and [LICENSE](LICENSE); the [upstream README](docs/upstream/README.md) is archived separately. Model-development provenance is recorded in [PROVENANCE.json](yolo_backprop/model_development/PROVENANCE.json).
