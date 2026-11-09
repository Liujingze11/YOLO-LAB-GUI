"""Create an atomic, independently editable YOLO dataset without changing its source."""
import json
from pathlib import Path
import shutil
import tempfile

import yaml

from yolo_backprop.data_screening.session import _key, _stamp
from .external import yolo_layout, _label_path, _linked


MARKER = '.yolo-backprop-dataset.json'


def organize_yolo(info, check_cancelled=lambda: None, progress=lambda *args: None):
    root = Path(info['root'])
    storage = Path(info['storage_root'])
    destination = storage / 'dataset'
    config = Path(info['dataset_yaml'])
    check_cancelled()
    if storage.is_symlink() or destination.is_symlink():
        raise ValueError('数据集工作目录不能是符号链接。')
    if destination.exists():
        try:
            marker = destination / MARKER
            if marker.is_symlink(): raise ValueError()
            saved = json.loads(marker.read_text(encoding='utf-8'))
            if saved != {'version': 1, 'source_root': str(root), 'source_config': str(config)}:
                raise ValueError()
            yolo_layout(destination, destination / 'data.yaml', check_cancelled)
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError('已有整理目录不可用，未覆盖任何文件：' + str(destination)) from exc
        return str(destination / 'data.yaml')
    config_stamp = _stamp(config)
    layout = yolo_layout(root, config, check_cancelled)
    files = {image for images in layout['splits'].values() for image in images}
    files.update(_label_path(image) for image in list(files) if _label_path(image).is_file())
    stamps = {path: _stamp(path) for path in files}
    stamps[config] = config_stamp
    storage.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.dataset-', dir=storage))
    try:
        document = {'names': layout['names']}
        total = sum(len(images) for images in layout['splits'].values()); done = 0
        for split, images in layout['splits'].items():
            document[split] = 'images/' + split
            image_dir = stage / 'images' / split; image_dir.mkdir(parents=True)
            used = set()
            for image in images:
                check_cancelled()
                stem, number = image.stem, 2
                while _key(stem) in used:
                    stem = image.stem + '_' + str(number); number += 1
                used.add(_key(stem))
                copies = [(image, image_dir / (stem + image.suffix))]
                label = _label_path(image)
                if label in stamps: copies.append((label, stage / 'labels' / split / (stem + '.txt')))
                for source, target in copies:
                    if _linked(source) or _stamp(source) != stamps[source]:
                        raise ValueError('整理时源文件发生变化：' + source.name)
                    target.parent.mkdir(parents=True, exist_ok=True)
                    with source.open('rb') as reader, target.open('xb') as writer:
                        while True:
                            check_cancelled()
                            chunk = reader.read(1024 * 1024)
                            if not chunk: break
                            writer.write(chunk)
                done += 1; progress(done, total, image.name)
        for path, stamp in stamps.items():
            check_cancelled()
            if _linked(path) or _stamp(path) != stamp:
                raise ValueError('整理时源文件发生变化：' + path.name)
        (stage / 'data.yaml').write_text(yaml.safe_dump(document, allow_unicode=True, sort_keys=False), encoding='utf-8')
        (stage / MARKER).write_text(json.dumps({'version': 1, 'source_root': str(root), 'source_config': str(config)}), encoding='utf-8')
        check_cancelled()
        if destination.exists(): raise ValueError('整理目录已存在，未覆盖任何文件。')
        stage.rename(destination)
    finally:
        if stage.exists(): shutil.rmtree(stage)
    return str(destination / 'data.yaml')
