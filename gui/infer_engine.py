"""
推理编排引擎 — 仅非交互模式，供 GUI 通过子进程调用。

入口：python gui/infer_engine.py --model ... --source ... --save-dir ... --conf ... --imgsz ...
"""
import json
import sys
import argparse
from pathlib import Path
from dataclasses import dataclass

# 子进程入口 — 确保项目根在 sys.path 中
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from ultralytics import YOLO

from gui.paths import PREDICT_DIR, BEST_SEG_MODEL, TEST_IMAGES_DIR

_ENGINE_DIR = Path(__file__).resolve().parent
_DEFAULT_TASK_PARAMS = _ENGINE_DIR / "infer_task_params.json"

# ── i18n locale helpers ─────────────────────────────────────
_LOCALE_DIR = Path(__file__).resolve().parent.parent / "locales"
_loc = None  # set in __main__

def _load_locale(lang: str) -> dict:
    path = _LOCALE_DIR / f"{lang}.json"
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _t(loc: dict, key: str, **kwargs) -> str:
    text = loc.get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except (KeyError, ValueError):
            pass
    return text


@dataclass
class InferConfig:
    model_path: str = BEST_SEG_MODEL
    source: str = TEST_IMAGES_DIR
    save_dir: str = str(Path(PREDICT_DIR) / "predict_result")
    conf: float = 0.406
    imgsz: int = 640
    task_param_file: str = str(_DEFAULT_TASK_PARAMS)
    out_suffix: str = "_overlay.jpg"


class TaskParamLoader:
    def __init__(self, json_path: str):
        self.json_path = Path(json_path)
        self.params = self._load_json()

    def _load_json(self) -> dict:
        if not self.json_path.exists():
            raise FileNotFoundError(_t(_loc, "找不到任务参数文件: {path}", path=self.json_path))
        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_task_params(self, task: str) -> dict:
        if task not in self.params:
            raise KeyError(_t(_loc, "配置文件里没有 task={task} 的参数", task=task))
        return self.params[task]


class YOLOInferencer:
    def __init__(self, cfg: InferConfig):
        self.cfg = cfg
        self.model = YOLO(self.cfg.model_path)
        self.task_loader = TaskParamLoader(self.cfg.task_param_file)
        self.save_dir = Path(self.cfg.save_dir)
        self.save_dir.mkdir(parents=True, exist_ok=True)
        self.task = self._detect_task()
        self.task_params = self.task_loader.get_task_params(self.task)

    def _detect_task(self) -> str:
        task = getattr(self.model, "task", None)
        if not task:
            raise ValueError(_t(_loc, "无法从模型中识别 task"))
        return task

    def _build_predict_kwargs(self) -> dict:
        kwargs = {
            "source": self.cfg.source,
            "imgsz": self.cfg.imgsz,
            "conf": self.cfg.conf,
            "save": False,
        }
        task_predict_kwargs = self.task_params.get("predict", {})
        kwargs.update(task_predict_kwargs)
        return kwargs

    def _build_plot_kwargs(self) -> dict:
        return self.task_params.get("plot", {})

    def run(self):
        print(_t(_loc, "infer.engine.model", path=self.cfg.model_path))
        print(_t(_loc, "infer.engine.task", task=self.task))
        print(_t(_loc, "infer.engine.source", source=self.cfg.source))
        print(_t(_loc, "infer.engine.output", dir=self.save_dir))

        predict_kwargs = self._build_predict_kwargs()
        plot_kwargs = self._build_plot_kwargs()

        results = self.model.predict(**predict_kwargs)

        for i, r in enumerate(results):
            if getattr(r, "path", None):
                stem = Path(r.path).stem
            else:
                stem = f"result_{i:05d}"
            out_path = self.save_dir / f"{stem}{self.cfg.out_suffix}"
            r.save(filename=str(out_path), **plot_kwargs)

        print(_t(_loc, "infer.engine.done", count=len(results), dir=self.save_dir))


# ── 子进程入口 ────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO inference engine (non-interactive)")
    parser.add_argument("--model", default=BEST_SEG_MODEL)
    parser.add_argument("--source", default=TEST_IMAGES_DIR)
    parser.add_argument("--save-dir", default=str(Path(PREDICT_DIR) / "predict_result"))
    parser.add_argument("--conf", type=float, default=0.406)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--lang", default="zh", help="Language code (zh/en/fr/es)")
    args = parser.parse_args()

    _loc = _load_locale(args.lang)

    cfg = InferConfig(
        model_path=args.model,
        source=args.source,
        save_dir=args.save_dir,
        conf=args.conf,
        imgsz=args.imgsz,
        task_param_file=str(_ENGINE_DIR / "infer_task_params.json"),
        out_suffix="_overlay.jpg",
    )

    inferencer = YOLOInferencer(cfg)
    inferencer.run()
