# YOLO Image Segmentation Training Lab

[阅读中文文档 (README_zh.md)](README_zh.md)

A small project built on Ultralytics YOLO for image segmentation training. The repository separates training flow, configuration management, logging, and validation to make experiments reproducible and easy to compare.

---

## Quick overview

- Goal: provide a reproducible and manageable segmentation training workflow (supports new training, resume from interruption, and fine-tuning from a historical best.pt).
- Language: Python 3.8+
- Dependencies: ultralytics, pyyaml (installation shown below)

---

## Key features

- Three training modes: new training / resume last run / continue from historical best.pt
- Pre-train confirmation that prints key parameters to avoid mistakes
- Toggleable data augmentation with centralized configuration
- Automatic validation and CSV logging (overall and per-class)
- Experiment isolation: each run creates its own result folder and logs for easy comparison

---

## Project structure (simplified)

```text
code/
├── dataset_tools/         # data splitting and label utilities
│   ├── create_empty_labels.py
│   ├── split_images_only/
│   │   ├── split_every_5th_images_only.py
│   │   └── split_random_images_only.py
│   ├── split_train_val/
│   │   ├── split_every_5th_with_labels.py
│   │   └── split_random_with_labels.py
│   └── split_train_val_test/
│       └── split_random_with_labels.py
├── pretrained_models/     # common pretrained weights (e.g. yolov8n.pt, yolov8n-seg.pt)
├── result/                # per-experiment result folders
├── scripts/               # training, config and logging scripts
│   ├── config.py
│   ├── paths.py
│   ├── train_logger.py
│   ├── train_segment.py
│   └── predict_test.py
├── train_logs/            # CSV logs: train_log / result_summary / result_per_class
├── data.yaml              # dataset config (classes, train/val paths)
├── data/                  # raw and prepared datasets (json_space, Source Data, datasets*)
├── predict/               # inference output images (overlay examples)
└── isat-sam/              # onnx models, class names and related files
```

---

## Setup

It is recommended to use a virtual environment:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install ultralytics pyyaml
```

If you use conda you can create and activate a conda environment instead:

```bash
conda create -n yolo python=3.8 -y
conda activate yolo
pip install -U pip
pip install ultralytics pyyaml
```

## Command-line options & non-interactive usage

The training script supports several command-line flags (via `argparse`) to override configuration at runtime: `--epochs`, `--imgsz`, `--batch`, `--device`, and `--name` (experiment name). The `--device` flag accepts GPU device specifiers as a string, e.g. `"0"`, `"0,1"`, or `"cpu"`.

Example (interactive mode, with prompts still shown):

```bash
python scripts/train_segment.py --epochs 200 --imgsz 1280 --batch 8 --device 0,1 --name my_experiment
```

The script will still prompt for the training mode (1/2/3), confirmation, and augmentation choice before starting. For full automation (CI, scripts), consider running the script inside a wrapper that feeds the expected inputs.

For GPU support, ensure the correct CUDA drivers and a matching PyTorch build are installed; Ultralytics uses the system PyTorch.

---

## Configuration

### Path auto-detection

Default paths are defined in `scripts/paths.py` and are **automatically derived from the project root** — no manual path editing is required if you follow the standard project structure. You only need to change them if your dataset or models are stored elsewhere.

### TrainConfig (`scripts/config.py`)

Training hyperparameters and experiment settings:

- Paths: `data_yaml`, `model_file`, `results_dir`, `log_dir` (default values imported from `paths.py`, auto-detected from project root)
- Training hyperparameters: `epochs`, `imgsz`, `batch`, `device`
- Experiment: `experiment_name` (used to generate `save_dir`)
- Augmentation: `use_augment` and parameters such as `hsv_h`, `hsv_s`, `hsv_v`, `translate`, `scale`, `mosaic`, `mixup`, `copy_paste`
- Auto properties: `save_dir`, `last_pt`, `best_pt` (computed via properties)

Note: training hyperparameters can be overridden at runtime via command-line arguments (see the "Command-line options" section): `--epochs`, `--imgsz`, `--batch`, `--device`, and `--name`.

---

## Quick start

1. Edit `data.yaml`: set the `path` to your dataset directory and update `names` with your class names.
2. (Optional) Edit `scripts/paths.py` if your dataset or models are in non-standard locations.
3. Start training:

```bash
python scripts/train_segment.py
```

The script will prompt for a training mode:

- Enter `1`: start a new training (uses `config.model_file` as the starting weights)
- Enter `2`: resume the last interrupted run (requires `last.pt` in the current experiment folder)
- Enter `3`: continue from a historical `best.pt` (scans `results_dir` and lets you pick an experiment)

Before training starts the script prints key parameters and asks whether to enable augmentation if not fixed in the config.

---

## Logs and validation

The project writes three CSV logs to `train_logs/`:

- `train_log.csv`: training process records (time, mode, status, paths, hyperparams, save locations, etc.)
- `result_summary_log.csv`: overall validation metrics (images/instances, box/mask mAP, precision/recall)
- `result_per_class_log.csv`: per-class metrics and sample distribution (useful to locate weak classes)

After training, validation runs automatically and results are appended to logs. The logs also include the number of images and instances per class found in the validation set.

---

## Recommended workflow

1. Prepare your dataset and `data.yaml` (use `dataset_tools/` for splitting if needed).
2. Set a new `experiment_name` in `scripts/config.py` to avoid collisions.
3. Run `python scripts/train_segment.py` and choose the appropriate mode.
4. After training, inspect `result/<experiment_name>/weights/` for `best.pt` and `last.pt`, and review corresponding entries in `train_logs/`.

---

## FAQ & tips

- To fine-tune from a specific historical model, use mode 3 and choose that experiment's `best.pt`.
- If `last.pt` is missing when selecting mode 2, the script will notify you and offer to start a new training instead.
- If GPU memory is insufficient, reduce `batch` or `imgsz`, or switch to CPU (`device='cpu'`) for reproducibility (slower).
- Consider including key hyperparameters (epochs/imgsz/batch) in `experiment_name` or saving them to the experiment folder for easier reproduction.

---

## dataset_tools

`dataset_tools/` contains utilities for preparing and splitting datasets so images and labels are organized for train/val/test workflows.

Main scripts and purpose:

- `dataset_tools/create_empty_labels.py` — generate empty YOLO-style label files for images without annotations (useful for placeholders or pseudo-labeling).
- `dataset_tools/split_images_only/` — split images only:
  - `split_every_5th_images_only.py`: sample every N-th image into val/test (periodic sampling).
  - `split_random_images_only.py`: randomly sample a proportion of images into val/test.
- `dataset_tools/split_train_val/` — split images and corresponding labels into train/val:
  - `split_every_5th_with_labels.py`: interval-based split and move matching label files.
  - `split_random_with_labels.py`: random split while keeping image/label pairs intact.
- `dataset_tools/split_train_val_test/` — support three-way splits (train/val/test), e.g. `split_random_with_labels.py` for independent test sets.

Usage tips:

- Back up original data or test the scripts on a copy before modifying your main dataset.
- Scripts typically accept source dir, target dir, and ratio/interval parameters — check top-of-file comments for usage.
- After splitting, verify that `data.yaml` `train`/`val`/`test` paths point to the correct locations.
- If your label format differs from standard YOLO (class x_center y_center w h per line), convert labels first.

These utilities speed up dataset preparation and reduce manual errors. Contributions for extra features (class-balanced sampling, resolution filters, etc.) are welcome.

---

## Future improvements

- Add a unified inference script and optional export (ONNX / TensorRT)
- Add visualization tools (training curves, confusion matrix, per-class comparisons)
- Auto-save training parameters as JSON/TXT into the experiment folder
- Add test-set evaluation and CI checks

---

## Contributing and maintenance

PRs and issues are welcome:
- improve validation scripts
- add compatibility notes for different Ultralytics versions

---

Final note: after large changes, update `experiment_name` and keep previous experiments for comparison and traceability.

## data.yaml example

A minimal `data.yaml` for a segmentation dataset should specify dataset paths and class names. Example:

```yaml
path: ./data/Source Data/datasets_all_pro   # absolute or relative path to dataset root
train: images/train
val: images/val
names:
  0: class_a
  1: class_b
  2: class_c
```

Ensure the `train` and `val` paths match your dataset layout (they may be absolute or relative to `path`).

## Where outputs and logs are stored

- Per-experiment results: `result/<experiment_name>/` (auto-created under project root)
- Checkpoints: `result/<experiment_name>/weights/last.pt` and `best.pt`
- CSV logs: `train_logs/` (auto-created) contains `train_log.csv`, `result_summary_log.csv` and `result_per_class_log.csv`
