"""设备自动检测 — 优先 GPU，无 GPU 则回退 CPU。"""
from __future__ import annotations


def get_default_device() -> str:
    """返回最佳可用设备：CUDA GPU → CPU。"""
    try:
        import torch
        if torch.cuda.is_available():
            return "0"
    except ImportError:
        pass
    return "cpu"


def get_available_devices() -> list[str]:
    """返回可用设备列表：['cpu'] 或 ['cpu', '0', '1', ...]."""
    devices = ["cpu"]
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                devices.append(str(i))
    except ImportError:
        pass
    return devices
