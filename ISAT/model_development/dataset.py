"""Freeze saved ISAT files into a separate, reproducible YOLO segmentation dataset."""
import hashlib
import json
import math
import os
from pathlib import Path
import random
import shutil
import tempfile
import uuid

import yaml
from PIL import Image
from ISAT.formats.yolo import YOLO


class DatasetCancelled(RuntimeError):
    pass


def _digest(path):
    result = hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''): result.update(chunk)
    return result.hexdigest()


def prepare_dataset(image_root, label_root, destination, categories, val_ratio=.2, seed=42,
                    check_cancelled=lambda: None, progress=lambda current, total, name: None,
                    ignore_background=True, keep_crowd=True):
    image_root, label_root, destination = [Path(p).expanduser().resolve() for p in [image_root, label_root, destination]]
    if not image_root.is_dir() or not label_root.is_dir(): raise ValueError('图像目录和标注目录必须存在')
    if destination.exists(): raise ValueError('输出目录已存在，请选择一个新目录，避免覆盖旧数据')
    if not 0 < val_ratio < 1: raise ValueError('验证集比例必须在 0 与 1 之间')
    if not categories or any(not isinstance(c, str) or not c.strip() for c in categories) or len(set(categories)) != len(categories): raise ValueError('类别名称必须有效且不能重复')
    names = [c for c in categories if not (ignore_background and c == '__background__')]
    if not names: raise ValueError('至少需要一个目标类别')
    mapping = {name: index for index, name in enumerate(names)}
    files = sorted(p for p in image_root.iterdir() if p.is_file() and p.suffix.lower() in {'.png', '.jpg', '.jpeg', '.bmp', '.webp', '.tif', '.tiff', '.gif', '.dcm'})
    stems = {}
    for file in files:
        if file.stem.casefold() in stems: raise ValueError('同名图片 stem 存在多个扩展名，无法唯一对应标注：'+file.name)
        stems[file.stem.casefold()] = file
    destination.parent.mkdir(parents=True, exist_ok=True)
    stage = Path(tempfile.mkdtemp(prefix='.'+destination.name+'-', dir=destination.parent))
    converter = YOLO(); converter.annos = {}; converter.cates = tuple(names)
    converter.ignore_background = ignore_background; converter.keep_crowd = True
    records, skipped, warnings, source_hashes = [], [], [], {}
    try:
        for index, source in enumerate(files):
            check_cancelled(); progress(index, len(files), source.name)
            label = label_root/(source.stem+'.json')
            if not label.is_file(): skipped.append(source.name); continue
            raw = label.read_bytes(); document = json.loads(raw)
            source_hashes[label] = hashlib.sha256(raw).hexdigest()
            if not isinstance(document, dict) or document.get('info', {}).get('description') != 'ISAT': raise ValueError('不是有效的 ISAT 标注：'+label.name)
            info = document['info']; width, height = info.get('width'), info.get('height')
            if type(width) is not int or type(height) is not int or width < 1 or height < 1: raise ValueError('标注图像尺寸无效：'+label.name)
            if info.get('name') and info['name'] != source.name: raise ValueError('标注中的图片名称不匹配：'+source.name)
            uid = hashlib.sha256(source.name.encode('utf-8')).hexdigest()[:20]
            master = stage/'annotations'/(uid+'.json'); master.parent.mkdir(exist_ok=True); master.write_bytes(raw)
            anno = converter.load_one_isat_json(str(master))
            kept = []
            for obj in anno.objs:
                if ignore_background and obj.category == '__background__': continue
                if not keep_crowd and obj.iscrowd: continue
                if obj.category not in mapping: raise ValueError('标注类别不在当前类别设置中：'+str(obj.category))
                points = obj.segmentation
                if not isinstance(points, (list, tuple)) or len(points) < 3 or any(not isinstance(p, (list, tuple)) or len(p) != 2 or any(type(v) not in [int, float] or not math.isfinite(v) for v in p) or not (0 <= p[0] <= width and 0 <= p[1] <= height) for p in points): raise ValueError('轮廓坐标无效或超出图像范围：'+label.name)
                from shapely.geometry import Polygon
                shape = Polygon(points)
                if not shape.is_valid or shape.area <= 0: raise ValueError('轮廓自交或面积为零：'+label.name)
                kept.append(obj)
            anno.objs = tuple(kept)
            source_hashes[source] = _digest(source)
            copied = stage/'source-images'/(uid+source.suffix.lower()); copied.parent.mkdir(exist_ok=True)
            shutil.copyfile(source, copied)
            if _digest(copied) != source_hashes[source]: raise ValueError('复制时源图片发生变化：'+source.name)
            if source.suffix.lower() == '.dcm':
                from ISAT.utils.dicom import load_dcm_as_image
                image = load_dcm_as_image(str(copied))
                canonical = True
            else:
                image = Image.open(copied)
                canonical = image.getexif().get(274, 1) != 1 or source.suffix.lower() in ['.tif', '.tiff', '.gif']
            if image.size != (width, height): image.close(); raise ValueError('图片实际尺寸与标注不一致：'+source.name)
            if canonical:
                converted = copied.with_suffix('.png')
                # Raw pixel orientation matches ISAT; stripping EXIF prevents a second rotation by YOLO.
                image.convert('RGB').save(converted); image.close()
                if converted != copied: copied.unlink()
                copied = converted; warnings.append('已为坐标一致性生成 PNG：'+source.name)
            else: image.close()
            text = stage/'temporary-labels'/(uid+'.txt'); text.parent.mkdir(exist_ok=True)
            converter.save_one_yolo_txt(anno, str(text), mapping)
            text.write_text(''.join(sorted(text.read_text().splitlines(keepends=True))), encoding='utf-8')
            records.append({'id': uid, 'name': source.name, 'source': str(source), 'label_source': str(label), 'source_sha256': source_hashes[source], 'annotation_sha256': source_hashes[label], 'annotation': master.relative_to(stage).as_posix(), 'image_sha256': _digest(copied), '_image': copied, '_label': text, 'objects': len(kept)})
        if len(records) < 2: raise ValueError('至少需要两张有已保存 ISAT 标注的图片；缺标注图片不会自动作为负样本')
        if not any(r['objects'] for r in records): raise ValueError('数据集中没有可训练的目标标注')
        groups = {}
        for record in records: groups.setdefault(record['image_sha256'], []).append(record)
        if len(groups) < 2: raise ValueError('至少需要两组内容不同的图片，避免相同图片进入训练集和验证集')
        keys = sorted(groups); random.Random(seed).shuffle(keys)
        count = max(1, min(len(keys)-1, round(len(keys)*val_ratio)))
        val_keys = set(keys[:count])
        if not any(r['objects'] and r['image_sha256'] not in val_keys for r in records):
            positive = next(r['image_sha256'] for r in records if r['objects'])
            replacement = next(key for key in keys if key not in val_keys)
            val_keys.remove(positive); val_keys.add(replacement)
        for record in records:
            check_cancelled()
            split = 'val' if record['image_sha256'] in val_keys else 'train'; record['split'] = split
            image = record.pop('_image'); label = record.pop('_label')
            image_out = stage/'images'/split/image.name; label_out = stage/'labels'/split/label.name
            image_out.parent.mkdir(parents=True, exist_ok=True); label_out.parent.mkdir(parents=True, exist_ok=True)
            image.rename(image_out); label.rename(label_out)
            record['image'] = image_out.relative_to(stage).as_posix(); record['label'] = label_out.relative_to(stage).as_posix()
        (stage/'temporary-labels').rmdir(); (stage/'source-images').rmdir()
        for source, digest in source_hashes.items():
            check_cancelled()
            if _digest(source) != digest: raise ValueError('准备期间源文件发生变化，请重试：'+source.name)
        data = {'path': str(destination), 'train': 'images/train', 'val': 'images/val', 'nc': len(names), 'names': dict(enumerate(names))}
        (stage/'data.yaml').write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False))
        manifest = {'schema_version': 1, 'dataset_id': uuid.uuid4().hex, 'categories': names, 'seed': seed, 'val_ratio': val_ratio, 'ignore_background': ignore_background, 'keep_crowd': keep_crowd, 'skipped': skipped, 'warnings': warnings, 'assets': records}
        (stage/'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2)+'\n')
        check_cancelled(); progress(len(files), len(files), '完成')
        if destination.exists(): raise ValueError('输出目录已被创建，未覆盖其内容')
        stage.rename(destination)
        return {'data_yaml': str(destination/'data.yaml'), 'train': [r['name'] for r in records if r['split'] == 'train'], 'val': [r['name'] for r in records if r['split'] == 'val'], 'skipped': skipped, 'warnings': warnings}
    except BaseException:
        shutil.rmtree(stage, ignore_errors=True)
        raise
