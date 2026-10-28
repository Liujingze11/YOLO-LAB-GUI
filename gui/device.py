"""设备自动检测 — 优先 GPU，无 GPU 则回退 CPU。"""
from __future__ import annotations

import platform

from gui.gpu_manager import is_cuda_available, has_gpu_ready_marker


def get_default_device() -> str:
    """返回最佳可用设备 ID：'0'（第一块 GPU）→ 'cpu'。"""
    try:
        if is_cuda_available():
            return "0"
    except Exception:
        pass
    return "cpu"


def get_available_devices() -> list[tuple[str, str]]:
    """返回可用设备列表：(device_id, display_name)。"""
    devices: list[tuple[str, str]] = [("cpu", "CPU")]
    try:
        import torch
        if is_cuda_available():
            for i in range(torch.cuda.device_count()):
                name = torch.cuda.get_device_name(i)
                total_mem = torch.cuda.get_device_properties(i).total_memory
                mem_gb = total_mem / (1024 ** 3)
                devices.append((str(i), f"GPU {i}: {name} ({mem_gb:.1f}G)"))
        else:
            if has_gpu_ready_marker():
                devices.append(("gpu", "GPU (需重启应用以启用)"))
            else:
                if platform.system() != "Darwin":
                    devices.append(("gpu", "GPU (点击检测)"))
                else:
                    try:
                        if torch.backends.mps.is_available():
                            devices.append(("mps", "Apple GPU (MPS)"))
                    except Exception:
                        pass
    except Exception:
        pass
    return devices
