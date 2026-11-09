"""Install the current source checkout in the Linux application menu."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

APP_ID = "yolo-backprop"


def _backup_entry(path):
    state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
    backup = state / APP_ID / "launcher-backups"
    backup.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, backup / (path.stem + "." + str(time.time_ns()) + ".desktop"))


def _value(text):
    """Escape a desktop-entry string value (before Exec argument quoting)."""
    return str(text).replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def _exec_argument(path):
    quoted = str(path).replace("%", "%%")
    for character in ('\\', '"', '`', '$'):
        quoted = quoted.replace(character, '\\' + character)
    return _value('"' + quoted + '"')


def install_launcher():
    """Install a distinct app identity and retire our legacy ISAT menu entry."""
    root = Path(__file__).resolve().parent.parent
    launcher = root / "run-yolo-backprop.sh"
    icon = root / "yolo_backprop" / "yolo-backprop-transparent.svg"
    if not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise RuntimeError("The source checkout must contain executable run-yolo-backprop.sh")
    if not icon.is_file():
        raise RuntimeError("Missing yolo-backprop-transparent.svg")

    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    applications = data / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    target = applications / (APP_ID + ".desktop")
    entry = "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        "Name=YOLO-BACKPROP",
        "Comment=Image annotation and YOLO model development",
        "Comment[zh_CN]=图像标注与 YOLO 模型训练、推理及导出",
        "Exec=" + _exec_argument(launcher),
        "TryExec=" + _value(launcher),
        "Icon=yolo-backprop",
        "Terminal=false",
        "StartupNotify=true",
        "StartupWMClass=" + APP_ID,
        "Categories=Graphics;",
        "Keywords=YOLO;BACKPROP;SAM;neural network;annotation;training;神经网络;标注;训练;",
        "",
    ])
    if target.exists() and target.read_text(encoding="utf-8") != entry:
        _backup_entry(target)

    icons = data / "icons/hicolor"
    scalable = icons / "scalable/apps"
    scalable.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(icon, scalable / "yolo-backprop.svg")
    # Publish a complete entry; desktop monitors see a replacement event.
    fd, name = tempfile.mkstemp(prefix="." + APP_ID + "-", suffix=".tmp", dir=applications)
    pending = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(entry)
        pending.chmod(0o755)
        pending.replace(target)
    finally:
        pending.unlink(missing_ok=True)

    legacy = applications / "ISAT.desktop"
    if legacy.is_file() and "Name=YOLO-BACKPROP" in legacy.read_text(encoding="utf-8").splitlines():
        _backup_entry(legacy)
        legacy.unlink()
    commands = [
        ["update-desktop-database", str(applications)],
        ["gtk-update-icon-cache", "--force", "--ignore-theme-index", str(icons)],
    ]
    for command in commands:
        if shutil.which(command[0]):
            subprocess.run(command, check=True)
    return target


if __name__ == "__main__":
    print(install_launcher())
