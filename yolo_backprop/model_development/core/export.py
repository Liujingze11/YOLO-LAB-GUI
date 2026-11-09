"""Model export logic — format-agnostic, shared across repos."""
from dataclasses import dataclass, field


# Format metadata: (display_name, emoji, description, ultralytics_format_key)
EXPORT_FORMATS: dict[str, dict] = {
    "onnx": {
        "key": "onnx",
        "emoji": "⚡",
        "desc_key": "export.format.onnx_desc",
        "suffix": ".onnx",
    },
    "engine": {
        "key": "engine",
        "emoji": "🚀",
        "desc_key": "export.format.engine_desc",
        "suffix": ".engine",
    },
    "openvino": {
        "key": "openvino",
        "emoji": "🔵",
        "desc_key": "export.format.openvino_desc",
        "suffix": "_openvino_model/",
    },
    "coreml": {
        "key": "coreml",
        "emoji": "🍎",
        "desc_key": "export.format.coreml_desc",
        "suffix": ".mlpackage",
    },
    "tflite": {
        "key": "tflite",
        "emoji": "📱",
        "desc_key": "export.format.tflite_desc",
        "suffix": ".tflite",
    },
}


@dataclass
class ExportConfig:
    model_path: str = ""
    format: str = "onnx"                # onnx / engine / openvino / coreml / tflite
    imgsz: int = 640
    output_dir: str = ""

    # ONNX options
    opset: int = 12
    dynamic: bool = True
    simplify: bool = True
    nms: bool = False

    # TensorRT options
    fp16: bool = False
    int8: bool = False
    workspace: float = 4.0              # GB


def build_export_kwargs(cfg: ExportConfig) -> dict:
    """Build kwargs dict for model.export() from ExportConfig."""
    kwargs: dict = {
        "format": cfg.format,
        "imgsz": cfg.imgsz,
    }
    if cfg.format == "onnx":
        kwargs["opset"] = cfg.opset
        kwargs["dynamic"] = cfg.dynamic
        kwargs["simplify"] = cfg.simplify
        if cfg.nms:
            kwargs["nms"] = True
    elif cfg.format == "engine":
        kwargs["half"] = cfg.fp16
        kwargs["int8"] = cfg.int8
        kwargs["workspace"] = cfg.workspace
    elif cfg.format == "openvino":
        kwargs["int8"] = cfg.int8
        if hasattr(cfg, "dynamic"):
            kwargs["dynamic"] = cfg.dynamic
    elif cfg.format == "coreml":
        if cfg.nms:
            kwargs["nms"] = True
    elif cfg.format == "tflite":
        kwargs["int8"] = cfg.int8
        if cfg.fp16:
            kwargs["half"] = True
    return kwargs


def build_export_arguments(cfg: ExportConfig) -> list[str]:
    arguments = ['--model', cfg.model_path, '--format', cfg.format, '--imgsz', str(cfg.imgsz), '--output-dir', cfg.output_dir]
    if cfg.format == 'onnx':
        arguments += ['--opset', str(cfg.opset), '--dynamic' if cfg.dynamic else '--no-dynamic', '--simplify' if cfg.simplify else '--no-simplify']
        if cfg.nms: arguments.append('--nms')
    elif cfg.format == 'engine':
        if cfg.fp16: arguments.append('--fp16')
        if cfg.int8: arguments.append('--int8')
        arguments += ['--workspace', str(cfg.workspace)]
    elif cfg.format == 'openvino':
        if cfg.int8: arguments.append('--int8')
        arguments.append('--dynamic' if cfg.dynamic else '--no-dynamic')
    elif cfg.format == 'coreml':
        if cfg.nms: arguments.append('--nms')
    elif cfg.format == 'tflite':
        if cfg.int8: arguments.append('--int8')
        if cfg.fp16: arguments.append('--fp16')
    return arguments
