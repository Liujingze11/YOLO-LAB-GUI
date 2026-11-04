"""Install the current source checkout in the Linux application menu."""

import os
from pathlib import Path
import shutil
import subprocess
import time


def _value(text):
    """Escape a desktop-entry string value (before Exec argument quoting)."""
    return str(text).replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r").replace("\t", "\\t")


def _exec_argument(path):
    quoted = str(path).replace("%", "%%")
    for character in ('\\', '"', '`', '$'):
        quoted = quoted.replace(character, '\\' + character)
    return _value('"' + quoted + '"')


def install_launcher():
    """Reuse ISAT.desktop and retain the previous entry outside the menu."""
    root = Path(__file__).resolve().parent.parent
    launcher = root / "run-isat.sh"
    icon = root / "ISAT" / "yolo-backprop-transparent.svg"
    if not launcher.is_file() or not os.access(launcher, os.X_OK):
        raise RuntimeError("The source checkout must contain executable run-isat.sh")
    if not icon.is_file():
        raise RuntimeError("Missing yolo-backprop-transparent.svg")

    data = Path(os.environ.get("XDG_DATA_HOME") or Path.home() / ".local/share")
    applications = data / "applications"
    applications.mkdir(parents=True, exist_ok=True)
    target = applications / "ISAT.desktop"
    entry = "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        "Name=YOLO-BACKPROP",
        "Comment=Image annotation and YOLO model development",
        "Comment[zh_CN]=图像标注与 YOLO 模型训练、推理及导出",
        "Exec=" + _exec_argument(launcher),
        "TryExec=" + _value(launcher),
        "Path=" + _value(root),
        "Icon=yolo-backprop",
        "Terminal=false",
        "StartupNotify=true",
        "StartupWMClass=ISAT",
        "Categories=Graphics;",
        "Keywords=YOLO;BACKPROP;ISAT;SAM;neural network;annotation;training;神经网络;标注;训练;",
        "",
    ])
    if target.exists() and target.read_text(encoding="utf-8") != entry:
        state = Path(os.environ.get("XDG_STATE_HOME") or Path.home() / ".local/state")
        backup = state / "isat-yolo" / "launcher-backups"
        backup.mkdir(parents=True, exist_ok=True)
        shutil.copy2(target, backup / ("ISAT." + str(time.time_ns()) + ".desktop"))

    icons = data / "icons/hicolor"
    scalable = icons / "scalable/apps"
    scalable.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(icon, scalable / "yolo-backprop.svg")
    target.write_text(entry, encoding="utf-8")
    target.chmod(0o755)
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
