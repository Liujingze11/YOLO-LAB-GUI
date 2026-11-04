"""Read-only recognition of image, ISAT and YOLO sources without application markers."""
import json
import math
from pathlib import Path
import re

import yaml

from ISAT.data_screening.session import ScreeningSession


def _scan(root):
    if root.is_symlink(): raise ValueError('图片目录不能是符号链接')
    session = ScreeningSession.scan(root)
    if not session.items: raise ValueError('文件夹内没有可读取的图片。')
    return session


def _isat(session):
    labelled = False
    for item in session.items:
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
        labelled = True
    return labelled


def _label_path(image):
    parts = list(image.parts)
    indices = [index for index, part in enumerate(parts) if part == 'images']
    if indices:
        parts[indices[-1]] = 'labels'
        return Path(*parts).with_suffix('.txt')
    return image.with_suffix('.txt')


def _yolo_label(path, classes):
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


def _split_images(value, base):
    entries = value if isinstance(value, list) else [value]
    result = []
    for entry in entries:
        if not isinstance(entry, str) or not entry.strip(): raise ValueError('YOLO 图片路径不能为空。')
        path = Path(entry).expanduser()
        if not path.is_absolute(): path = base / path
        if path.is_symlink(): raise ValueError('YOLO 图片路径不能是符号链接。')
        if path.is_dir():
            result.extend(item.source for item in _scan(path).items)
        elif path.is_file() and path.suffix.lower() == '.txt':
            from PIL import Image
            for line in path.read_text(encoding='utf-8-sig').splitlines():
                if not line.strip(): continue
                image = Path(line.strip()).expanduser()
                choices = [image] if image.is_absolute() else [path.parent / image, base / image]
                image = next((choice for choice in choices if choice.is_file() and not choice.is_symlink()), None)
                if image is None: raise ValueError('YOLO 图片清单中有不存在的图片。')
                with Image.open(image) as source: source.verify()
                result.append(image.resolve())
        else:
            raise ValueError('YOLO 图片路径不存在：' + str(path))
    if not result: raise ValueError('YOLO 数据集没有可读取的图片。')
    return result


def _yolo(root, config):
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
            names = list(normalized.values())
        if not isinstance(names, list) or not names or any(not isinstance(name, str) or not name.strip() for name in names):
            raise ValueError()
        if 'nc' in document and (type(document['nc']) is not int or document['nc'] != len(names)): raise ValueError()
        base = Path(document.get('path') or root).expanduser()
        if not base.is_absolute(): base = root / base
        images = []
        for split in ('train', 'val', 'test'):
            if split != 'train' and not document.get(split): continue
            images.extend(_split_images(document.get(split), base))
        for image in images: _yolo_label(_label_path(image), len(names))
    except (OSError, ValueError, TypeError, SyntaxError, yaml.YAMLError) as exc:
        raise ValueError('YOLO 数据配置或标签有误：' + str(exc)) from exc
    return {'source_kind': 'yolo', 'source_images': str(images[0].parent),
            'sample_image': str(images[0]), 'dataset_yaml': str(config)}


def recognize(root):
    """Require readable content, not pre-created application directory names."""
    root = Path(root)
    for name in ('data.yaml', 'data.yml', 'dataset.yaml', 'dataset.yml'):
        config = root / name
        if config.exists() or config.is_symlink(): return _yolo(root, config)
    images = root / 'images'
    if not images.is_dir():
        images = root
        projects = root / 'projects'
        if projects.is_dir() and not projects.is_symlink():
            images = next((project / 'images' for project in sorted(projects.iterdir())
                           if project.is_dir() and not project.is_symlink() and (project / 'images').is_dir()), root)
    if (root / 'json').is_symlink(): raise ValueError('标注目录不能是符号链接。')
    session = _scan(images)
    labelled = _isat(session)
    return {'source_kind': 'isat' if labelled else 'images', 'source_images': str(images),
            'sample_image': str(session.items[0].source), 'dataset_yaml': ''}
