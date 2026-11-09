"""Read-only recognition of image, ISAT and YOLO sources without application markers."""
import json
import math
from pathlib import Path
import re

import yaml

from yolo_backprop.data_screening.session import ScreeningSession


def _linked(path):
    return any(part.is_symlink() for part in (path, *path.parents))


def _scan(root, check_cancelled=lambda: None):
    if _linked(root): raise ValueError('图片目录不能是符号链接')
    session = ScreeningSession.scan(root, check_cancelled)
    if not session.items: raise ValueError('文件夹内没有可读取的图片。')
    return session


def _isat(session, check_cancelled=lambda: None):
    labelled = 0
    for item in session.items:
        check_cancelled()
        if item.annotation is None: continue
        label = item.annotation
        if label.is_symlink() or label.parent.is_symlink():
            raise ValueError('标注不能通过符号链接读取：' + label.name)
        try:
            value = json.loads(label.read_text(encoding='utf-8'))
            info = value.get('info', {}) if isinstance(value, dict) else {}
            if (not isinstance(info, dict) or info.get('description') != 'ISAT'
                    or type(info.get('width')) is not int or type(info.get('height')) is not int
                    or info.get('width') != item.width or info.get('height') != item.height
                    or not isinstance(value.get('objects'), list)):
                raise ValueError()
            if info.get('name') and info['name'] != item.source.name: raise ValueError()
            for obj in value['objects']:
                if not isinstance(obj, dict) or not isinstance(obj.get('category'), str) or not obj['category'].strip():
                    raise ValueError()
                points = obj.get('segmentation')
                if not isinstance(points, list) or len(points) < 3: raise ValueError()
                for point in points:
                    if (not isinstance(point, list) or len(point) != 2
                            or any(type(number) not in (int, float) or not math.isfinite(number) for number in point)
                            or not 0 <= point[0] <= item.width or not 0 <= point[1] <= item.height):
                        raise ValueError()
        except (OSError, ValueError, TypeError) as exc:
            raise ValueError('ISAT 标注格式或图片尺寸不匹配：' + label.name) from exc
        labelled += 1
    return labelled


def _label_path(image):
    parts = list(image.parts)
    indices = [index for index, part in enumerate(parts) if part == 'images']
    if indices:
        parts[indices[-1]] = 'labels'
        return Path(*parts).with_suffix('.txt')
    return image.with_suffix('.txt')


def _yolo_label(path, classes):
    if _linked(path): raise ValueError('YOLO 标签路径不能是符号链接：' + str(path))
    if not path.exists(): return  # Missing labels are valid unlabelled images.
    if path.is_symlink() or path.parent.is_symlink() or not path.is_file():
        raise ValueError('YOLO 标签路径无效：' + str(path))
    try:
        for row in path.read_text(encoding='utf-8-sig').splitlines():
            values = row.split()
            if not values: continue
            if not re.fullmatch(r'\d+', values[0]) or int(values[0]) >= classes:
                raise ValueError()
            if len(values) != 5 and (len(values) < 7 or len(values) % 2 != 1):
                raise ValueError()
            coordinates = [float(value) for value in values[1:]]
            if not all(math.isfinite(value) and 0 <= value <= 1 for value in coordinates):
                raise ValueError()
            if len(values) == 5 and (coordinates[2] <= 0 or coordinates[3] <= 0):
                raise ValueError()
    except (OSError, ValueError) as exc:
        raise ValueError('YOLO 标签格式或类别不正确：' + path.name + '，请检查标签内容。') from exc


def _split_images(value, base, check_cancelled=lambda: None):
    entries = value if isinstance(value, list) else [value]
    result = []
    for entry in entries:
        check_cancelled()
        if not isinstance(entry, str) or not entry.strip(): raise ValueError('YOLO 图片路径不能为空。')
        path = Path(entry).expanduser()
        if not path.is_absolute(): path = base / path
        if _linked(path): raise ValueError('YOLO 图片路径不能是符号链接。')
        if path.is_dir():
            result.extend(item.source for item in _scan(path, check_cancelled).items)
        elif path.is_file() and path.suffix.lower() == '.txt':
            from PIL import Image
            for line in path.read_text(encoding='utf-8-sig').splitlines():
                check_cancelled()
                if not line.strip(): continue
                image = Path(line.strip()).expanduser()
                choices = [image] if image.is_absolute() else [path.parent / image, base / image]
                image = next((choice for choice in choices if choice.is_file() and not choice.is_symlink()), None)
                if image is None: raise ValueError('YOLO 图片清单中有不存在的图片。')
                if _linked(image): raise ValueError('YOLO 图片路径不能是符号链接。')
                with Image.open(image) as source: source.verify()
                result.append(image.resolve())
        else:
            raise ValueError('YOLO 图片路径不存在：' + str(path))
    if not result: raise ValueError('YOLO 数据集没有可读取的图片。')
    return result


def yolo_layout(root, config, check_cancelled=lambda: None):
    if config.is_symlink(): raise ValueError('YOLO 配置不能是符号链接。')
    try:
        document = yaml.safe_load(config.read_text(encoding='utf-8'))
        if not isinstance(document, dict): raise ValueError()
        names = document.get('names')
        if isinstance(names, dict):
            if any(type(key) is not int and not (isinstance(key, str) and key.isdigit()) for key in names):
                raise ValueError()
            normalized = {int(key): value for key, value in names.items()}
            if len(normalized) != len(names) or set(normalized) != set(range(len(names))): raise ValueError()
            names = [normalized[index] for index in range(len(normalized))]
        if not isinstance(names, list) or not names or any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError()
        if 'nc' in document and (type(document['nc']) is not int or document['nc'] != len(names)): raise ValueError()
        base = Path(document.get('path') or root).expanduser()
        if not base.is_absolute(): base = root / base
        splits = {}
        for split in ('train', 'val', 'test'):
            if split != 'train' and not document.get(split): continue
            splits[split] = list(dict.fromkeys(_split_images(document.get(split), base, check_cancelled)))
        for images in splits.values():
            for image in images:
                check_cancelled()
                _yolo_label(_label_path(image), len(names))
    except (OSError, ValueError, TypeError, SyntaxError, yaml.YAMLError) as exc:
        raise ValueError('YOLO 数据配置或标签有误：' + str(exc)) from exc
    return {'names': names, 'splits': splits}


def _yolo(root, config, check_cancelled=lambda: None):
    layout = yolo_layout(root, config, check_cancelled)
    images = list(dict.fromkeys(image for split in layout['splits'].values() for image in split))
    return {'source_kind': 'yolo', 'source_images': str(images[0].parent),
            'sample_image': str(images[0]), 'dataset_yaml': str(config),
            'image_count': len(images), 'annotation_count': sum(_label_path(image).is_file() for image in images),
            'split_counts': {key: len(value) for key, value in layout['splits'].items()}}


def recognize(root, check_cancelled=lambda: None):
    """Identify data without modifying it or guessing missing annotation schemas."""
    root = Path(root)
    candidates = []
    conventional = {'data.yaml', 'data.yml', 'dataset.yaml', 'dataset.yml'}
    for config in sorted(root.iterdir()):
        check_cancelled()
        if config.name in conventional:
            candidates.append(config)
        elif config.suffix.lower() in ('.yaml', '.yml') and config.is_file() and not config.is_symlink():
            try:
                value = yaml.safe_load(config.read_text(encoding='utf-8'))
                if isinstance(value, dict) and 'train' in value and 'names' in value:
                    candidates.append(config)
            except (OSError, ValueError, yaml.YAMLError): pass
    if len(candidates) > 1:
        raise ValueError('发现多个 YOLO 数据配置，无法自动确定使用哪一个：' + '、'.join(p.name for p in candidates))
    if candidates: return _yolo(root, candidates[0], check_cancelled)
    images = root / 'images'
    if not images.is_dir():
        images = root
        projects = root / 'projects'
        if projects.is_dir() and not projects.is_symlink():
            images = next((project / 'images' for project in sorted(projects.iterdir())
                           if project.is_dir() and not project.is_symlink() and (project / 'images').is_dir()), root)
    if (root / 'json').is_symlink(): raise ValueError('标注目录不能是符号链接。')
    session = _scan(images, check_cancelled)
    labelled = _isat(session, check_cancelled)
    if any(_label_path(item.source).is_file() for item in session.items):
        raise ValueError('发现 YOLO 标签，但缺少数据配置。请提供包含类别 names 和图片划分的 data.yaml 后打开。')
    return {'source_kind': 'isat' if labelled else 'images', 'source_images': str(images),
            'sample_image': str(session.items[0].source), 'dataset_yaml': '',
            'image_count': len(session.items), 'annotation_count': labelled,
            'skipped_count': len(session.skipped)}
