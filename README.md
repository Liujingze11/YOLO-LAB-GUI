# YOLO Lab GUI

[中文](README_zh.md) | [Français](README_fr.md) | [Español](README_es.md)

Desktop YOLO segmentation training/inference tool with Apple-style minimalist UI.

## Features

- **Train** — New/Resume/Fine-tune modes, data augmentation, preset management
- **Inference** — Image segmentation with progress tracking
- **Tools** — Dataset splitting, empty label creation
- **Logs & Results** — Historical training logs and experiment browsing
- Auto-download initial weights from dropdown
- Dark/Light mode toggle
- 4-language support (zh/en/fr/es) for GUI and terminal output
- Subprocess execution with stop capability

## Quick Start

```bash
git clone https://github.com/Liujingze11/YOLO-LAB-GUI.git
cd YOLO-LAB-GUI
bash setup.sh
conda activate yolo
python gui/main.py
```

## Requirements

- Python 3.10+
- [Miniconda](https://docs.conda.io/en/latest/miniconda.html)
- ultralytics >= 8.0.0, PySide6 >= 6.5.0, PyYAML >= 6

Manual install:

```bash
conda create -n yolo python=3.10 -y
conda activate yolo
pip install -r requirements.txt
```

## Project Structure

```
YOLO-LAB-GUI/
├── gui/                    # Desktop UI (PySide6)
│   ├── main.py             # Main window + entry point
│   ├── styles.py           # Colors & style constants (light/dark themes)
│   ├── widgets.py          # Widget factory functions
│   ├── model_selector.py   # Model selector with auto-download dialog
│   ├── i18n.py             # Multi-language translation manager
│   ├── workers.py          # Background training/inference threads
│   ├── config.py           # TrainConfig data class
│   ├── device.py           # Auto device detection
│   ├── paths.py            # Path definitions
│   ├── train_engine.py     # Training orchestration (3 modes)
│   ├── train_logger.py     # CSV logging
│   └── infer_engine.py     # Inference engine
├── locales/                # Translation files (zh/en/fr/es)
├── tools/dataset_tools/    # Dataset splitting & label utilities
├── pretrained_models/      # Pretrained model cache
├── data.yaml               # Dataset configuration
├── setup.sh                # One-click environment setup
├── environment.yml         # Conda environment definition
└── requirements.txt
```

## Usage

### Training

1. Switch to the Train tab
2. Configure `data.yaml`, hyperparameters, and training mode
3. Click Start Training

Three modes:
- **New** — From initial weights
- **Resume** — Continue from last.pt
- **Fine-tune** — Based on a historical experiment's best.pt

### Inference

1. Switch to the Inference tab
2. Select model, source, and output directory
3. Click Start Inference

### Language

Use the dropdown in the top-right corner to switch between Chinese / English / Français / Español. All UI text and subprocess terminal output updates instantly.

## Outputs

- Training results: `outputs/results/<experiment_name>/weights/` (best.pt, last.pt)
- Inference results: `outputs/predict/`
- CSV logs: `outputs/logs/`

## data.yaml Format

```yaml
path: data/datasets
train: images/train
val: images/val
names:
  0: class_a
  1: class_b
```

## License

MIT
