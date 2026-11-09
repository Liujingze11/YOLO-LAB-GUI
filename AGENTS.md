# Repository workflow

- GUI and CLI are independent repositories; do not merge their source trees.
- Keep `main` as the only local and remote development branch. Work directly on `main`; do not create feature branches or worktrees unless the user explicitly requests one.
- Preserve Git history when integrating changes. Do not force-push or restore the retired GUI / Electron implementation.
- Use one agent and work sequentially.
- Keep personal `yolo_backprop/software.yaml`, `.runtime/`, model weights and generated datasets local. Do not force-add ignored settings or runtime files.
- Run GUI regression tests with `QT_QPA_PLATFORM=offscreen PYTHONPATH=.runtime/python:. python -m unittest discover -s tests -v`, using an interpreter with the project dependencies installed.
- Current application: native PyQt5 YOLO-BACKPROP. Launch with `./run-yolo-backprop.sh`.
