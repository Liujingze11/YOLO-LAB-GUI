"""
推理编排引擎 — 仅非交互模式，供 GUI 通过子进程调用。

入口：python gui/infer_engine.py --model ... --source ... --save-dir ... --conf ... --imgsz ...
"""
import json
import argparse
from pathlib import Path
from dataclasses import dataclass

from ultralytics import YOLO

from gui.paths import PREDICT_DIR, BEST_SEG_MODEL, TEST_IMAGES_DIR

_SCRIPTS_DIR = Path(__file__).resolve().parent
_DEFAULT_TASK_PARAMS = _SCRIPTS_DIR / "infer_task_params.json"


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
            raise FileNotFoundError(f"找不到任务参数文件: {self.json_path}")
        with open(self.json_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def get_task_params(self, task: str) -> dict:
        if task not in self.params:
            raise KeyError(f"配置文件里没有 task={task} 的参数")
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
            raise ValueError("无法从模型中识别 task")
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
        print(f"模型: {self.cfg.model_path}")
        print(f"自动识别任务: {self.task}")
        print(f"输入源: {self.cfg.source}")
        print(f"输出目录: {self.save_dir}")

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

        print(f"推理完成，共保存 {len(results)} 张结果到: {self.save_dir}")


# ── 子进程入口 ────────────────────────────────────────────

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="YOLO inference engine (non-interactive)")
    parser.add_argument("--model", default=BEST_SEG_MODEL)
    parser.add_argument("--source", default=TEST_IMAGES_DIR)
    parser.add_argument("--save-dir", default=str(Path(PREDICT_DIR) / "predict_result"))
    parser.add_argument("--conf", type=float, default=0.406)
    parser.add_argument("--imgsz", type=int, default=640)
    args = parser.parse_args()

    cfg = InferConfig(
        model_path=args.model,
        source=args.source,
        save_dir=args.save_dir,
        conf=args.conf,
        imgsz=args.imgsz,
        task_param_file=str(_SCRIPTS_DIR / "infer_task_params.json"),
        out_suffix="_overlay.jpg",
    )

    inferencer = YOLOInferencer(cfg)
    inferencer.run()
