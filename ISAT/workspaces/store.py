"""Workspace metadata and recent locations; never move existing project data."""
import json
import hashlib
import os
from pathlib import Path
import re
import shutil
import tempfile
import time
import uuid

from PIL import Image, ImageOps
from PyQt5 import QtCore
import yaml

from ISAT.data_screening.session import IMAGE_SUFFIXES
from ISAT.data_screening.workspace import WorkspaceSettings, _atomic_json


MARKER = '.yolo-backprop-workspace.json'


def validate_project_name(name):
    if (not isinstance(name, str) or not name.strip() or name != name.strip()
            or name.startswith('.') or name.endswith('.') or len(name) > 80
            or any(ord(c) < 32 or ord(c) == 127 or c in '/\\<>:"|?*' for c in name)
            or re.fullmatch(r'CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9]', name.split('.')[0], re.IGNORECASE)):
        raise ValueError('请填写有效的项目名称，不要包含路径或特殊字符')


def _image_in(path):
    if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES:
        return path
    if path.is_dir():
        return next((p for p in path.rglob('*') if p.is_file()
                     and p.suffix.lower() in IMAGE_SUFFIXES), None)
    return None


def training_image(data_yaml):
    """Resolve a picture from the actual YOLO training split, including TXT lists."""
    try:
        config = Path(data_yaml).expanduser().resolve()
        document = yaml.safe_load(config.read_text(encoding='utf-8'))
        if not isinstance(document, dict): return None
        root = Path(document.get('path') or config.parent).expanduser()
        if not root.is_absolute(): root = config.parent / root
        splits = document.get('train', [])
        for entry in splits if isinstance(splits, list) else [splits]:
            if not isinstance(entry, str) or not entry: continue
            split = Path(entry).expanduser()
            if not split.is_absolute(): split = root / split
            if split.suffix.lower() == '.txt' and split.is_file():
                with split.open(encoding='utf-8-sig') as stream:
                    for line in stream:
                        value = line.strip()
                        if not value: continue
                        image = Path(value).expanduser()
                        choices = [image] if image.is_absolute() else [split.parent / image, root / image]
                        for choice in choices:
                            if choice.is_file() and choice.suffix.lower() in IMAGE_SUFFIXES:
                                return choice.resolve()
            else:
                image = _image_in(split)
                if image: return image.resolve()
    except (OSError, ValueError, TypeError, yaml.YAMLError):
        pass
    return None


class WorkspaceStore:
    def __init__(self, path=None):
        self.path = Path(path) if path else WorkspaceSettings().path.with_name('workspaces.json')

    def _external_root(self, root):
        base = self.path.expanduser().resolve().parent / 'external-projects'
        identity = str(root)
        try:
            stat = root.stat()
            identity += '\x00' + str(stat.st_dev) + ':' + str(stat.st_ino)
        except OSError:
            pass
        storage = base / hashlib.sha256(identity.encode('utf-8')).hexdigest()
        if base.is_symlink() or storage.is_symlink():
            raise ValueError('外部项目工作目录不能是符号链接。')
        return storage

    def _external_info(self, root, details=None):
        storage = self._external_root(root)
        marker = storage / MARKER
        document = {'version': 1, 'name': root.name, 'state': {}, 'last_opened': 0, 'trained': False}
        if marker.exists() or marker.is_symlink():
            try:
                if marker.is_symlink(): raise ValueError()
                document = json.loads(marker.read_text(encoding='utf-8'))
                if (not isinstance(document, dict) or document.get('version') != 1
                        or document.get('source_root') != str(root) or document.get('external') is not True
                        or not isinstance(document.get('name'), str) or not document['name']
                        or not isinstance(document.get('state'), dict)
                        or not isinstance(document.get('source_images'), str)):
                    raise ValueError()
                if not Path(document['source_images']).is_dir(): raise ValueError()
            except (OSError, ValueError, TypeError) as exc:
                raise ValueError('外部项目工作记录不可用：' + str(root)) from exc
        else:
            if details is None:
                from .external import recognize
                details = recognize(root)
        if details: document.update(details)
        document.update(root=str(root), storage_root=str(storage), external=True, source_root=str(root))
        cover = storage / '.yolo-backprop' / 'cover.jpg'
        document['cover'] = str(cover) if cover.is_file() else document.get('sample_image', '')
        return document

    @staticmethod
    def _document(info):
        return {key: value for key, value in info.items() if key not in ('root', 'cover', 'storage_root')}

    @staticmethod
    def _record(info):
        return {key: info.get(key, False) for key in ('root', 'name', 'legacy', 'external', 'storage_root')}

    def _metadata_path(self, root):
        marker = root / MARKER
        return marker if marker.exists() or marker.is_symlink() else self._external_root(root) / MARKER

    def has_metadata(self, root):
        try:
            root = self._checked_root(root)
            marker = self._metadata_path(root)
            return root.is_dir() and marker.is_file() and not marker.is_symlink()
        except (OSError, ValueError, RuntimeError):
            return False

    def _is_protected_location(self, root):
        home = Path.home().resolve()
        if root == root.parent or root == home or root in home.parents:
            return True
        if os.name == 'posix' and root.parent == Path('/'):
            return True
        if self.path.expanduser().resolve().is_relative_to(root):
            return True
        names = ('Desktop', '桌面', 'Documents', '文档', 'Downloads', '下载', 'Pictures', '图片',
                 'Music', '音乐', 'Videos', '视频', 'Public', '公共的', 'Templates', '模板')
        protected = {home / name for name in names}
        for kind in (QtCore.QStandardPaths.DesktopLocation, QtCore.QStandardPaths.DocumentsLocation,
                     QtCore.QStandardPaths.DownloadLocation, QtCore.QStandardPaths.PicturesLocation,
                     QtCore.QStandardPaths.MusicLocation, QtCore.QStandardPaths.MoviesLocation):
            protected.update(Path(value).expanduser().resolve()
                             for value in QtCore.QStandardPaths.standardLocations(kind) if value)
        return root in protected

    def _checked_root(self, root):
        root = Path(root).expanduser()
        if root.is_symlink(): raise ValueError('项目文件夹不能是符号链接')
        root = root.resolve()
        if self._is_protected_location(root):
            raise ValueError('桌面、主目录等公共位置不能直接作为项目，请在其中新建命名的项目文件夹。')
        return root

    def prune_unsafe_locations(self):
        """Remove mistaken common-folder selections from configuration only."""
        records = self._records()
        safe = []
        for row in records:
            try:
                if self._is_protected_location(Path(row['root']).expanduser().resolve()): continue
            except (OSError, ValueError, RuntimeError): continue
            safe.append(row)
        if safe != records: self._save_records(safe)
        settings = WorkspaceSettings(self.path.with_name('workspace.json'))
        if settings.root is not None and self._is_protected_location(settings.root):
            _atomic_json(settings.path, {'version': 1, 'root': None})

    def _records(self):
        try:
            records = json.loads(self.path.read_text(encoding='utf-8'))['workspaces']
            if not isinstance(records, list): return []
            return [row for row in records if isinstance(row, dict)
                    and isinstance(row.get('root'), str) and row['root']]
        except (OSError, ValueError, KeyError, TypeError):
            return []

    def read(self, root):
        root = self._checked_root(root)
        if not root.is_dir(): raise ValueError('工作空间目录不存在：' + str(root))
        marker = root / MARKER
        if marker.is_symlink(): raise ValueError('项目记录不能是符号链接')
        if not marker.exists():
            if (self._external_root(root) / MARKER).exists(): return self._external_info(root)
            from .external import recognize
            try: details = recognize(root)
            except ValueError:
                if not (root / 'projects').is_dir(): raise
            else: return self._external_info(root, details)
        document = {'version': 1, 'name': root.name, 'state': {}, 'last_opened': 0, 'trained': False}
        if marker.exists():
            try:
                value = json.loads(marker.read_text(encoding='utf-8'))
                if (not isinstance(value, dict) or value.get('version') != 1
                        or not isinstance(value.get('name'), str) or not value['name']
                        or not isinstance(value.get('state', {}), dict)):
                    raise ValueError()
                document.update(value)
            except (OSError, ValueError, TypeError) as exc:
                raise ValueError('工作空间记录损坏：' + str(root)) from exc
        elif not (root / 'projects').is_dir():
            raise ValueError('请选择已有 YOLO-BACKPROP 工作空间')
        if (root / 'projects').is_symlink(): raise ValueError('工作空间 projects 不能是符号链接')
        cover = root / '.yolo-backprop' / 'cover.jpg'
        document['root'] = str(root)
        document['storage_root'] = str(root)
        document['external'] = False
        document['cover'] = str(cover) if cover.is_file() else ''
        return document

    def create(self, parent, name):
        validate_project_name(name)
        parent = Path(parent).expanduser().resolve()
        if not parent.is_dir(): raise ValueError('请先选择保存位置')
        root = self._checked_root(parent / name)
        root.mkdir()  # An existing folder is never reused or overwritten.
        try:
            stat = root.stat()
            (root / 'projects').mkdir()
            _atomic_json(root / MARKER, {'version': 1, 'name': name, 'state': {},
                                        'ownership': {'id': uuid.uuid4().hex, 'parent': str(parent), 'name': name,
                                                      'device': stat.st_dev, 'inode': stat.st_ino},
                                        'created_at': time.time(), 'last_opened': 0, 'trained': False})
            self.register(root)
        except BaseException:
            shutil.rmtree(root)
            raise
        return root

    def open_location(self, location):
        """Open an existing project only; never initialize the selected parent."""
        self.read_existing(location)
        return self.register(location)

    def read_existing(self, root):
        """Validate a picked project without adopting or modifying a directory."""
        root = self._checked_root(root)
        if not root.is_dir(): raise ValueError('项目目录不存在：' + str(root))
        marker = root / MARKER
        if marker.exists() or marker.is_symlink(): return self.read(root)
        from .external import recognize
        return self._external_info(root, recognize(root))

    def validate_deletion(self, root):
        info = self.read(root)
        root = Path(info['root'])
        ownership = info.get('ownership')
        stat = root.stat()
        if (info.get('external') or not isinstance(ownership, dict)
                or not isinstance(ownership.get('id'), str)
                or not re.fullmatch('[0-9a-f]{32}', ownership['id'])
                or ownership.get('parent') != str(root.parent)
                or ownership.get('name') != root.name or info['name'] != root.name
                or type(ownership.get('device')) is not int or ownership['device'] != stat.st_dev
                or type(ownership.get('inode')) is not int or ownership['inode'] != stat.st_ino):
            raise ValueError('无法确认该文件夹由软件新建，请使用“从列表移除”，文件会保留。')
        return info

    def register(self, root):
        root = self._checked_root(root)
        info = self.read(root)
        document = self._document(info)
        document['last_opened'] = time.time()
        storage = Path(info['storage_root'])
        if info['external']:
            storage.mkdir(parents=True, exist_ok=True)
            if (storage / 'projects').is_symlink(): raise ValueError('工作目录 projects 不能是符号链接。')
            (storage / 'projects').mkdir(exist_ok=True)
        _atomic_json(storage / MARKER, document)
        records = [self._record(row)
                   for row in self.recent() if row['root'] != str(root)]
        records.insert(0, self._record(info))
        self._save_records(records[:30])
        return root

    def _save_records(self, records):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json(self.path, {'version': 1, 'workspaces': records})

    def forget(self, root, descendants=False):
        root = Path(root).expanduser().resolve()
        def matches(value):
            path = Path(value)
            return path == root or (descendants and path.is_relative_to(root))
        recent = self.recent()
        removed_storage = {str(self._external_root(Path(row['root']))) for row in recent
                           if matches(row['root']) and row.get('external')}
        removed_storage.add(str(self._external_root(root)))
        base = self.path.expanduser().resolve().parent / 'external-projects'
        for row in self._records():
            value = row.get('storage_root')
            if matches(row['root']) and isinstance(value, str):
                storage = Path(value)
                if storage.parent == base and re.fullmatch('[0-9a-f]{64}', storage.name):
                    removed_storage.add(str(storage))
        records = [self._record(row) for row in recent if not matches(row['root'])]
        self._save_records(records)
        settings = WorkspaceSettings(self.path.with_name('workspace.json'))
        if settings.root is not None and (matches(settings.root) or str(settings.root) in removed_storage):
            _atomic_json(settings.path, {'version': 1, 'root': None})

    def update(self, root, **fields):
        root = Path(root).expanduser().resolve()
        if not self.has_metadata(root): raise ValueError('项目已被删除：' + str(root))
        info = self.read(root)
        storage = Path(info['storage_root'])
        document = self._document(info); document.update(fields)
        _atomic_json(storage / MARKER, document)

    def recent(self):
        records = self._records()
        # Adopt the old single remembered location without rewriting its files.
        if not self.path.exists():
            previous = WorkspaceSettings(self.path.with_name('workspace.json')).root
            if previous and (previous / 'projects').is_dir():
                records.append({'root': str(previous), 'name': previous.name, 'legacy': True})
        result, seen = [], set()
        for row in records:
            try: root = str(Path(row['root']).expanduser().resolve())
            except (OSError, ValueError, RuntimeError): continue
            if root in seen: continue
            if row.get('external') and not (self._external_root(Path(root)) / MARKER).is_file(): continue
            legacy = not (Path(root) / MARKER).is_file() and not row.get('external')
            if legacy and row.get('legacy') is not True: continue
            try: info = dict(self.read(row['root']), available=True, legacy=legacy)
            except (OSError, ValueError, RuntimeError): continue
            seen.add(root)
            result.append(info)
        return result

    def set_cover(self, root, image, trained=False):
        root = Path(root).resolve()
        info = self.read(root)
        directory = Path(info['storage_root']) / '.yolo-backprop'
        if directory.is_symlink(): raise ValueError('工作空间缓存目录不能是符号链接')
        directory.mkdir(exist_ok=True)
        fd, temporary = tempfile.mkstemp(prefix='.cover-', suffix='.jpg', dir=directory)
        os.close(fd)
        try:
            with Image.open(image) as source:
                source.thumbnail((640, 480))
                thumbnail = ImageOps.exif_transpose(source).convert('RGB')
                thumbnail.save(temporary, 'JPEG', quality=85)
            os.replace(temporary, directory / 'cover.jpg')
            self.update(root, trained=bool(trained))
        finally:
            if os.path.exists(temporary): os.unlink(temporary)
