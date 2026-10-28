"""GPU detection, CUDA compatibility check, and download management."""
from __future__ import annotations

import json
import os
import platform
import subprocess
import sys
import urllib.request
from pathlib import Path

from PySide6.QtCore import QThread, Signal

from gui.paths import get_user_data_dir, is_frozen
from gui.i18n import tr


def get_gpu_dir() -> Path:
    return get_user_data_dir() / "gpu"


def get_gpu_ready_file() -> Path:
    return get_gpu_dir() / "gpu_ready.json"


def is_cuda_available() -> bool:
    """Check if CUDA torch is already available."""
    gpu_dir = str(get_gpu_dir())
    if has_gpu_ready_marker() and gpu_dir not in sys.path:
        sys.path.insert(0, gpu_dir)
    try:
        import torch
        return torch.cuda.is_available()
    except ImportError:
        return False


def has_gpu_ready_marker() -> bool:
    return get_gpu_ready_file().is_file()


def _check_nvidia_driver() -> tuple:
    """Check if NVIDIA driver is present. Returns (has_driver, gpu_name)."""
    try:
        result = subprocess.run(
            ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"],
            capture_output=True, text=True, timeout=10
        )
        if result.returncode == 0 and result.stdout.strip():
            name = result.stdout.strip().split("\n")[0]
            return True, name
    except (FileNotFoundError, subprocess.TimeoutExpired):
        pass
    return False, ""


def _check_amd_driver() -> bool:
    """Check if AMD GPU driver is present."""
    try:
        result = subprocess.run(
            ["rocm-smi"], capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_gpu_capability() -> dict:
    """Check system GPU capability. Returns status dict.

    Returns:
        {
            "status": "cuda_ready" | "needs_download" | "needs_restart"
                     | "dev_needs_cuda_torch" | "no_nvidia" | "has_amd"
                     | "macos_mps" | "cpu_only",
            "gpu_name": str or None,
            "download_size_gb": float or None,
            "message": str,
        }
    """
    system = platform.system()

    # macOS
    if system == "Darwin":
        import torch
        try:
            if torch.backends.mps.is_available():
                return {"status": "macos_mps", "gpu_name": "Apple GPU (MPS)", "download_size_gb": None, "message": ""}
        except Exception:
            pass
        return {"status": "cpu_only", "gpu_name": None, "download_size_gb": None, "message": ""}

    # Already has CUDA torch working
    if is_cuda_available():
        import torch
        name = torch.cuda.get_device_name(0) if torch.cuda.device_count() > 0 else "NVIDIA GPU"
        return {"status": "cuda_ready", "gpu_name": name, "download_size_gb": None, "message": ""}

    # GPU bundle installed but not yet loaded (needs restart)
    if has_gpu_ready_marker():
        return {
            "status": "needs_restart",
            "gpu_name": None,
            "download_size_gb": None,
            "message": tr("gpu.restart_needed"),
        }

    # Check NVIDIA driver
    has_nvidia, gpu_name = _check_nvidia_driver()
    if has_nvidia:
        if is_frozen():
            return {
                "status": "needs_download",
                "gpu_name": gpu_name,
                "download_size_gb": 2.5,
                "message": tr("gpu.download_prompt").format(name=gpu_name, size="2.5"),
            }
        else:
            return {
                "status": "dev_needs_cuda_torch",
                "gpu_name": gpu_name,
                "download_size_gb": None,
                "message": tr("gpu.dev_needs_cuda_torch").format(name=gpu_name),
            }

    # Check AMD
    if _check_amd_driver():
        return {"status": "has_amd", "gpu_name": None, "download_size_gb": None, "message": tr("gpu.no_amd")}

    # No GPU
    return {"status": "no_nvidia", "gpu_name": None, "download_size_gb": None, "message": tr("gpu.no_nvidia")}


class GpuDownloadWorker(QThread):
    """Background thread for downloading CUDA components."""
    progress = Signal(int, int)
    finished = Signal(bool, str)
    error_msg = Signal(str)

    def __init__(self, download_url: str, dest_dir: Path):
        super().__init__()
        self._url = download_url
        self._dest = dest_dir / "gpu_bundle.zip"
        self._tmp = dest_dir / "gpu_bundle.zip.tmp"
        self._aborted = False

    def run(self) -> None:
        try:
            self._dest.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(self._url) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                with open(self._tmp, "wb") as f:
                    while True:
                        if self._aborted:
                            self._cleanup()
                            return
                        chunk = resp.read(65536)
                        if not chunk:
                            break
                        f.write(chunk)
                        downloaded += len(chunk)
                        self.progress.emit(downloaded, total)
            if self._aborted:
                self._cleanup()
                return
            os.replace(str(self._tmp), str(self._dest))
            self._install_bundle()
            self.finished.emit(True, self._dest.name)
        except Exception as exc:
            self._cleanup()
            self.error_msg.emit(str(exc))
            self.finished.emit(False, str(exc))

    def _install_bundle(self) -> None:
        """Extract gpu_bundle.zip into the gpu directory."""
        import zipfile
        from datetime import datetime
        dest_dir = self._dest.parent
        with zipfile.ZipFile(self._dest, "r") as zf:
            zf.extractall(dest_dir)
        ready = {"cuda_version": "cu121", "installed_at": datetime.now().isoformat()}
        with open(dest_dir / "gpu_ready.json", "w") as f:
            json.dump(ready, f)
        self._dest.unlink(missing_ok=True)

    def stop(self) -> None:
        self._aborted = True

    def _cleanup(self) -> None:
        if self._tmp.is_file():
            self._tmp.unlink(missing_ok=True)


class GpuInstallWorker(QThread):
    """Background thread for pip-installing CUDA torch in dev mode."""
    log_line = Signal(str)
    finished = Signal(bool, str)

    def __init__(self):
        super().__init__()
        self._process: subprocess.Popen | None = None
        self._aborted = False

    def run(self) -> None:
        index_url = "https://download.pytorch.org/whl/cu121"
        cmd = [
            sys.executable, "-m", "pip", "install",
            "--force-reinstall",
            "torch", "torchvision",
            "--index-url", index_url,
        ]
        try:
            self._process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            self.finished.emit(False, str(e))
            return

        for line in self._process.stdout:
            if self._aborted:
                self._process.terminate()
                self._process.wait()
                return
            stripped = line.rstrip()
            if stripped:
                self.log_line.emit(stripped)

        self._process.wait()
        if self._aborted:
            return
        if self._process.returncode == 0:
            self.finished.emit(True, "CUDA torch installed")
        else:
            self.finished.emit(False, f"pip exit code: {self._process.returncode}")

    def stop(self) -> None:
        self._aborted = True
        if self._process and self._process.poll() is None:
            self._process.terminate()
            try:
                self._process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait()
