"""
Model export engine — subprocess entry point for model format conversion.

Usage: python gui/export_engine.py --model best.pt --format onnx --imgsz 640 --output-dir ./exports
"""
import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ultralytics import YOLO
from core.export import ExportConfig, build_export_kwargs


def parse_args():
    p = argparse.ArgumentParser(description="YOLO model export engine")
    p.add_argument("--model", required=True)
    p.add_argument("--format", default="onnx", choices=["onnx", "engine", "openvino", "coreml", "tflite"])
    p.add_argument("--imgsz", type=int, default=640)
    p.add_argument("--output-dir", default="")
    p.add_argument("--opset", type=int, default=12)
    p.add_argument("--dynamic", action="store_true", default=True)
    p.add_argument("--no-dynamic", action="store_false", dest="dynamic")
    p.add_argument("--simplify", action="store_true", default=True)
    p.add_argument("--no-simplify", action="store_false", dest="simplify")
    p.add_argument("--nms", action="store_true", default=False)
    p.add_argument("--fp16", action="store_true", default=False)
    p.add_argument("--int8", action="store_true", default=False)
    p.add_argument("--workspace", type=float, default=4.0)
    p.add_argument("--lang", default="zh")
    return p.parse_args()


def main():
    args = parse_args()

    # i18n
    _locale_dir = Path(__file__).resolve().parent.parent / "locales"
    from core.i18n import load_locale, t as _t
    loc = load_locale(_locale_dir, args.lang)

    cfg = ExportConfig(
        model_path=args.model,
        format=args.format,
        imgsz=args.imgsz,
        output_dir=args.output_dir,
        opset=args.opset,
        dynamic=args.dynamic,
        simplify=args.simplify,
        nms=args.nms,
        fp16=args.fp16,
        int8=args.int8,
        workspace=args.workspace,
    )

    print(_t(loc, "export.engine.loading", model=cfg.model_path))
    model = YOLO(cfg.model_path)

    task = getattr(model, "task", "detect")
    print(_t(loc, "export.engine.task", task=task))

    if cfg.output_dir:
        Path(cfg.output_dir).mkdir(parents=True, exist_ok=True)

    kwargs = build_export_kwargs(cfg)

    print(_t(loc, "export.engine.exporting", format=cfg.format, imgsz=cfg.imgsz))
    try:
        result_path = model.export(**kwargs)
        print(_t(loc, "export.engine.done", path=result_path))
    except Exception as e:
        print(_t(loc, "export.engine.failed", err=str(e)))
        sys.exit(1)


if __name__ == "__main__":
    main()
