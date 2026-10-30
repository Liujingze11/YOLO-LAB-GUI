"""Opt-in real CPU train -> inference -> ONNX; never downloads models or dependencies."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from ISAT.model_development.dataset import prepare_dataset
from ISAT.model_development.core.config import TrainConfig, save_run_config


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--weights', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    output = args.output.resolve(); output.mkdir(parents=True, exist_ok=True)
    images, labels = output/'source-images', output/'source-labels'
    images.mkdir(exist_ok=True); labels.mkdir(exist_ok=True)
    template = json.loads((ROOT/'tests/fixtures/sample.json').read_text())
    for index in range(6):
        image = Image.new('RGB', (512, 384), (210 + index, 215, 225))
        draw = ImageDraw.Draw(image)
        for obj, color in zip(template['objects'], ['#ef2929', '#fcaf3e']): draw.polygon([tuple(p) for p in obj['segmentation']], fill=color)
        image.save(images/f'image{index}.png')
        data = json.loads(json.dumps(template)); data['info']['name'] = f'image{index}.png'
        (labels/f'image{index}.json').write_text(json.dumps(data))
    dataset = prepare_dataset(images, labels, output/'dataset', ['__background__', 'person', 'knife'])
    config = TrainConfig(data_yaml=dataset['data_yaml'], model_file=str(args.weights.resolve()), results_dir=str(output/'runs'), log_dir=str(output/'logs'), epochs=1, imgsz=64, batch=2, device='cpu', experiment_name='smoke', use_augment=False, close_mosaic=0, multi_scale=0, warmup_epochs=0)
    config_file = output/'run-config.yaml'; save_run_config(config, config_file)
    env = {**os.environ, 'YOLO_AUTOINSTALL': 'false', 'MPLBACKEND': 'Agg', 'OMP_NUM_THREADS': '2', 'MKL_NUM_THREADS': '2', 'OPENBLAS_NUM_THREADS': '2', 'YOLO_CONFIG_DIR': str(output/'ultralytics'), 'ISAT_MODEL_DATA_DIR': str(output/'settings')}
    def run(name, arguments):
        with (output/(name+'.log')).open('w') as log:
            result = subprocess.run([sys.executable, *map(str, arguments)], cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, timeout=240)
        if result.returncode:
            print((output/(name+'.log')).read_text()[-6500:]); raise RuntimeError(name+' exited '+str(result.returncode))
    engine = ROOT/'ISAT/model_development/gui'
    run('train', [engine/'train_engine.py', '--no-interactive', '--config-file', config_file, '--mode', 1, '--no-augment'])
    best = output/'runs/smoke/weights/best.pt'
    assert best.is_file(), 'training publishes best.pt'
    assert (output/'runs/smoke/results.csv').is_file(), 'training produces metrics'
    run('infer', [engine/'infer_engine.py', '--model', best, '--source', images, '--save-dir', output/'predict', '--imgsz', 64])
    assert len(list((output/'predict').glob('*_overlay.jpg'))) == 6, 'inference writes six overlays'
    run('export', [engine/'export_engine.py', '--model', best, '--format', 'onnx', '--imgsz', 64, '--output-dir', output/'onnx', '--no-dynamic', '--no-simplify'])
    assert (output/'onnx/best.onnx').is_file(), 'export uses the selected output directory'
    assert not best.with_suffix('.onnx').exists(), 'export leaves the source weights directory unchanged'
    import onnxruntime as ort
    import numpy as np
    session = ort.InferenceSession(str(output/'onnx/best.onnx'), providers=['CPUExecutionProvider'])
    result = session.run(None, {session.get_inputs()[0].name: np.zeros((1, 3, 64, 64), dtype=np.float32)})
    assert len(result) >= 1 and all(np.isfinite(array).all() for array in result)
    (output/'verification.json').write_text(json.dumps({'train': str(best), 'inference_images': 6, 'onnx': str(output/'onnx/best.onnx'), 'onnx_runtime_outputs': [list(array.shape) for array in result]}, indent=2))
    print('CPU train, inference, ONNX export and ONNX Runtime passed:', output)


if __name__ == '__main__': main()
