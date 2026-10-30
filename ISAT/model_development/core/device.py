"""GPU device detection utilities."""
from __future__ import annotations


def get_default_device() -> str:
    """Return '0' if CUDA is available, otherwise 'cpu'."""
    try:
        import torch
        if torch.cuda.is_available():
            return "0"
    except Exception:
        pass
    return "cpu"


def get_available_devices() -> list[tuple[str, str]]:
    """Return list of (device_id, display_name) tuples.

    Always includes ('cpu', 'CPU').  For each GPU, adds ('N', 'GPU N: Name (X.XG)').
    """
    devices: list[tuple[str, str]] = [("cpu", "CPU")]
    try:
        import torch
        for i in range(torch.cuda.device_count()):
            name = torch.cuda.get_device_name(i)
            try:
                total_gb = torch.cuda.get_device_properties(i).total_memory / (1024 ** 3)
                display = f"GPU {i}: {name} ({total_gb:.1f}G)"
            except Exception:
                display = f"GPU {i}: {name}"
            devices.append((str(i), display))
    except Exception:
        pass
    return devices
