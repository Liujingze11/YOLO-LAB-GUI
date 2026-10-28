"""First-run setup wizard — shown once on initial launch."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from core.paths import MODEL_REGISTRY
from gui.paths import PRETRAINED_DIR, ensure_user_dirs
from gui.i18n import tr
from gui.styles import COLOR_ACCENT, COLOR_TEXT, COLOR_TEXT_MUTED

_WELCOME_MARKER = PRETRAINED_DIR / ".welcome_shown"


def is_first_run() -> bool:
    return not _WELCOME_MARKER.exists()


def mark_welcome_done() -> None:
    _WELCOME_MARKER.parent.mkdir(parents=True, exist_ok=True)
    _WELCOME_MARKER.write_text("")


class WelcomeWizard(QDialog):
    """Show first-run system status summary and guidance."""

    def __init__(self, parent: QWidget | None = None):
        super().__init__(parent)
        self.setWindowTitle(tr("welcome.title"))
        self.setFixedSize(480, 420)
        self.setModal(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 24, 30, 24)
        layout.setSpacing(14)

        title = QLabel(tr("welcome.heading"))
        title.setStyleSheet(f"font-size: 20px; font-weight: 600; color: {COLOR_ACCENT};")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        info = QLabel(self._build_summary())
        info.setStyleSheet(f"font-size: 13px; color: {COLOR_TEXT};")
        info.setWordWrap(True)
        layout.addWidget(info)

        layout.addStretch()

        tip = QLabel(tr("welcome.tip"))
        tip.setStyleSheet(f"font-size: 11px; color: {COLOR_TEXT_MUTED};")
        tip.setWordWrap(True)
        tip.setAlignment(Qt.AlignCenter)
        layout.addWidget(tip)

        btn = QPushButton(tr("welcome.start"))
        btn.setStyleSheet(
            f"QPushButton {{ background: {COLOR_ACCENT}; color: #fff; border: none; "
            f"border-radius: 6px; padding: 10px 32px; font-size: 14px; font-weight: 500; }}"
            f"QPushButton:hover {{ opacity: 0.9; }}"
        )
        btn.clicked.connect(self.accept)
        layout.addWidget(btn, alignment=Qt.AlignCenter)

        mark_welcome_done()

    def _build_summary(self) -> str:
        lines = ["", tr("welcome.env_summary"), ""]

        # GPU status
        from gui.gpu_manager import check_gpu_capability
        cap = check_gpu_capability()
        status = cap["status"]
        if status == "cuda_ready":
            lines.append(f"🟢 GPU: {cap['gpu_name']} — {tr('welcome.gpu_ready')}")
        elif status in ("needs_download", "needs_restart"):
            lines.append(f"🟡 GPU: {tr('welcome.gpu_need_setup')}")
        elif status == "dev_needs_cuda_torch":
            lines.append(f"🟡 GPU: {cap['gpu_name']} {tr('welcome.gpu_need_cuda')}")
        elif status == "macos_mps":
            lines.append(f"🟢 GPU: {cap['gpu_name']} — {tr('welcome.gpu_ready')}")
        else:
            lines.append(f"⚪ GPU: {tr('welcome.gpu_cpu')}")

        # Models available
        local = sum(1 for fn, _, _ in MODEL_REGISTRY if (PRETRAINED_DIR / fn).is_file())
        total = len(MODEL_REGISTRY)
        lines.append(f"{'🟢' if local > 0 else '⚪'} {tr('welcome.models')}: {local}/{total}")

        # Data dirs
        ensure_user_dirs()
        lines.append(f"🟢 {tr('welcome.data_ready')}")

        return "\n".join(lines)
