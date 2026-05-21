"""设备自动检测 — 优先 GPU，无 GPU 则回退 CPU。"""
from __future__ import annotations


def get_default_device() -> str:
    """返回最佳可用设备 ID：'0'（第一块 GPU）→ 'cpu'。"""
    try:
        import torch
        if torch.cuda.is_available():
            return "0"
    except ImportError:
        pass
    return "cpu"


def get_available_devices() -> list[tuple[str, str]]:
    """返回可用设备列表：(device_id, display_name)。"""
    devices: list[tuple[str, str]] = [("cpu", "CPU")]
    try:
        import torch
        if torch.cuda.is_available():
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                total_mem = torch.cuda.get_device_properties(i).total_memory
                mem_gb = total_mem / (1024 ** 3)
                devices.append((str(i), f"GPU {i}: {name} ({mem_gb:.1f}G)"))
    except ImportError:
        pass
    return devices
