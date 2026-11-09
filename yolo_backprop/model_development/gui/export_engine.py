"""
Model export engine — subprocess entry point for model format conversion.

Usage: python gui/export_engine.py --model best.pt --format onnx --imgsz 640 --output-dir ./exports
"""
import sys
import argparse
import shutil
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from ultralytics import YOLO
from yolo_backprop.model_development.core.export import ExportConfig, build_export_kwargs


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
    from yolo_backprop.model_development.core.i18n import load_locale, t as _t
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
    destination = Path(cfg.output_dir).expanduser().resolve() if cfg.output_dir else Path(cfg.model_path).resolve().parent
    destination.mkdir(parents=True, exist_ok=True)
    try:
        # Export from a private copy: Ultralytics writes beside its input checkpoint.
        with tempfile.TemporaryDirectory(prefix='.yolo-backprop-export-', dir=destination) as temporary:
            source = Path(temporary)/Path(cfg.model_path).name
            shutil.copyfile(cfg.model_path, source)
            model = YOLO(str(source))
            print(_t(loc, "export.engine.task", task=getattr(model, 'task', 'detect')))
            print(_t(loc, "export.engine.exporting", format=cfg.format, imgsz=cfg.imgsz))
            generated = Path(model.export(**build_export_kwargs(cfg))).resolve()
            output = destination/generated.name
            if output.exists():
                raise FileExistsError('Output already exists; select a new directory: '+str(output))
            generated.rename(output)
        print(_t(loc, "export.engine.done", path=str(output)))
    except Exception as exc:
        print(_t(loc, "export.engine.failed", err=str(exc)))
        sys.exit(1)


if __name__ == "__main__":
    main()
