"""Non-destructive screening records and isolated ISAT project creation."""
from dataclasses import dataclass
import json
import os
from pathlib import Path
import shutil
import tempfile
import unicodedata

from PIL import Image
import yaml


IMAGE_SUFFIXES = {'.jpg', '.jpeg', '.png', '.bmp', '.webp', '.tif', '.tiff', '.gif', '.ppm', '.pgm', '.pbm'}


def _stamp(path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns


def _key(stem):
    return unicodedata.normalize('NFC', stem).casefold()


@dataclass(eq=False)
class ScreeningItem:
    source: Path
    name: str
    width: int
    height: int
    stamp: tuple
    annotation: object = None
    annotation_stamp: object = None
    record_id: str = ''


class ScreeningSession:
    def __init__(self, root, items, skipped):
        self.root = root
        self.items = items
        self.skipped = skipped
        self.trash = []
        self.project_root = None

    @classmethod
    def scan(cls, root, check_cancelled=lambda: None, progress=lambda current, total, name: None):
        root = Path(root).expanduser().resolve()
        if not root.is_dir():
            raise ValueError('请拖入一个存在的图片文件夹')
        candidates = []
        for directory, dirs, files in os.walk(root):
            check_cancelled()
            dirs[:] = sorted(d for d in dirs if not d.startswith('.') and not Path(directory, d).is_symlink())
            candidates.extend(Path(directory, f) for f in sorted(files)
                              if not f.startswith('.') and Path(f).suffix.lower() in IMAGE_SUFFIXES
                              and not Path(directory, f).is_symlink())
        items, skipped, used = [], [], set()
        for index, source in enumerate(candidates):
            check_cancelled()
            try:
                stamp = _stamp(source)
                with Image.open(source) as image:
                    width, height = image.size
                    image.verify()
                if stamp != _stamp(source):
                    raise ValueError('扫描时文件发生变化')
            except (OSError, ValueError, SyntaxError) as exc:
                skipped.append((str(source), str(exc)))
                progress(index + 1, len(candidates), source.name)
                continue
            stem, counter = source.stem, 2
            while _key(stem) in used:
                stem = source.stem + '_' + str(counter)
                counter += 1
            used.add(_key(stem))
            label = source.with_suffix('.json')
            if not label.is_file() and root.name in ('images', '图片'):
                label = root.parent / 'json' / source.relative_to(root).with_suffix('.json')
            if not label.is_file():
                label = None
            items.append(ScreeningItem(source, stem + source.suffix, width, height, stamp,
                                       label, _stamp(label) if label else None))
            progress(index + 1, len(candidates), source.name)
        return cls(root, items, skipped)

    def rename(self, item, stem):
        stem = stem.strip()
        if (item not in self.items or not stem or stem in ('.', '..') or stem.startswith('.')
                or any(char in stem for char in '/\\\x00\n\r\t')):
            raise ValueError('文件名不能为空，也不能包含路径分隔符或控制字符')
        if any(other is not item and _key(Path(other.name).stem) == _key(stem) for other in self.items + self.trash):
            raise ValueError('已有同名图片，请使用另一个名称')
        item.name = stem + item.source.suffix

    def remove(self, items):
        removed = set(items)
        self.trash.extend(item for item in self.items if item in removed)
        self.items[:] = [item for item in self.items if item not in removed]

    def restore(self, items):
        restored = set(items)
        self.items.extend(item for item in self.trash if item in restored)
        self.trash[:] = [item for item in self.trash if item not in restored]

    def save_project(self, check_cancelled=lambda: None, progress=lambda *args: None, categories=None):
        from .workspace import save_project
        return save_project(self, check_cancelled, progress, categories)

    def purge_trash(self):
        from .workspace import save_project
        return save_project(self, purge=True)

    def export_project(self, destination, check_cancelled=lambda: None,
                       progress=lambda current, total, name: None, categories=None):
        destination = Path(destination).expanduser().resolve()
        if destination.exists():
            raise ValueError('项目文件夹已存在，未覆盖任何内容，请另选位置')
        if not self.items:
            raise ValueError('没有保留的图片，请先选择图片文件夹')
        destination.parent.mkdir(parents=True, exist_ok=True)
        stage = Path(tempfile.mkdtemp(prefix='.' + destination.name + '-', dir=destination.parent))
        try:
            images = stage / 'images'; images.mkdir()
            labels = stage / 'json'; labels.mkdir()
            for index, item in enumerate(self.items):
                check_cancelled()
                try:
                    if _stamp(item.source) != item.stamp:
                        raise ValueError('源图片发生变化，请重新打开文件夹：' + item.source.name)
                    with item.source.open('rb') as source, (images / item.name).open('xb') as target:
                        while True:
                            check_cancelled()
                            chunk = source.read(1024 * 1024)
                            if not chunk: break
                            target.write(chunk)
                    if _stamp(item.source) != item.stamp:
                        raise ValueError('复制时源图片发生变化：' + item.source.name)
                    if item.annotation:
                        if _stamp(item.annotation) != item.annotation_stamp:
                            raise ValueError('源标注发生变化：' + item.annotation.name)
                        document = json.loads(item.annotation.read_text(encoding='utf-8'))
                        if not isinstance(document, dict):
                            raise ValueError('不是有效的 ISAT 标注：' + item.annotation.name)
                        info = document.get('info', {})
                        if (not isinstance(info, dict) or info.get('description') != 'ISAT'
                                or info.get('width') != item.width or info.get('height') != item.height
                                or not isinstance(document.get('objects'), list)):
                            raise ValueError('标注格式或图像尺寸不匹配：' + item.annotation.name)
                        info['name'] = item.name
                        info['folder'] = str(destination / 'images')
                        (labels / (Path(item.name).stem + '.json')).write_text(
                            json.dumps(document, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
                except OSError as exc:
                    raise ValueError('无法读取或复制图片/标注：' + item.source.name + '\n' + str(exc)) from exc
                progress(index + 1, len(self.items), item.name)
            for item in self.items:
                check_cancelled()
                try:
                    if _stamp(item.source) != item.stamp or (item.annotation and _stamp(item.annotation) != item.annotation_stamp):
                        raise ValueError('生成期间源文件发生变化，请重新打开文件夹：' + item.source.name)
                except OSError as exc:
                    raise ValueError('生成期间源文件不可用：' + item.source.name) from exc
            if categories is not None:
                (labels / 'isat.yaml').write_text(yaml.safe_dump({'label': categories}, allow_unicode=True), encoding='utf-8')
            check_cancelled()
            if destination.exists():
                raise ValueError('项目文件夹已被创建，未覆盖任何内容')
            stage.rename(destination)
        except BaseException:
            shutil.rmtree(stage, ignore_errors=True)
            raise
        return {'project_root': str(destination), 'image_root': str(destination / 'images'),
                'label_root': str(destination / 'json'), 'files': [item.name for item in self.items]}
