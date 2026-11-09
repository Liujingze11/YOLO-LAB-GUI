"""Owned local projects: originals are copied once; saves replace a staged snapshot."""
import json
import os
import re
from pathlib import Path
import shutil
import tempfile
import uuid

import yaml

from .session import ScreeningSession, ScreeningItem, _key, _stamp, IMAGE_SUFFIXES


MARKER = '.yolo-backprop-project.json'


def _atomic_json(path, document):
    fd, temporary = tempfile.mkstemp(prefix='.write-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(document, stream, ensure_ascii=False, indent=2); stream.write('\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def _write_manifest(root, document):
    _atomic_json(root / MARKER, document)


def _valid_name(name):
    return (isinstance(name, str) and name and not name.startswith('.')
            and not any(c in name for c in '/\\\x00\r\n\t')
            and Path(name).suffix.lower() in IMAGE_SUFFIXES)


def _paths(root, entry):
    base = root / '.trash' if entry['trash'] else root
    return base / 'images' / entry['name'], base / 'json' / (Path(entry['name']).stem + '.json')


def _safe_file(root, path, required=True):
    if (not path.is_relative_to(root) or path.is_symlink()
            or any(p.is_symlink() for p in path.parents if p != root and p.is_relative_to(root))
            or not path.resolve().is_relative_to(root)):
        raise ValueError('项目路径不安全，未修改任何文件：' + str(path))
    if path.exists() and not path.is_file(): raise ValueError('项目文件不是普通文件：' + str(path))
    if required and not path.is_file(): raise ValueError('项目副本不存在：' + str(path))


def _read_manifest(root):
    _safe_file(root, root / MARKER)
    document = json.loads((root / MARKER).read_text(encoding='utf-8'))
    if (not isinstance(document, dict) or document.get('version') != 1
            or not isinstance(document.get('id'), str) or not re.fullmatch('[0-9a-f]{32}', document['id'])
            or not isinstance(document.get('entries'), list) or not isinstance(document.get('source_root'), str)):
        raise ValueError('不是 YOLO-BACKPROP 筛选项目')
    used, ids = set(), set()
    for entry in document['entries']:
        if not isinstance(entry, dict) or not {'id', 'name', 'trash', 'width', 'height'} <= entry.keys():
            raise ValueError('筛选项目清单包含不完整记录')
        name = entry['name']; key = _key(Path(name).stem) if isinstance(name, str) else ''
        if (not _valid_name(name) or key in used or not isinstance(entry['trash'], bool)
                or not isinstance(entry['id'], str) or not re.fullmatch('[0-9a-f]{32}', entry['id']) or entry['id'] in ids
                or any(type(entry[k]) is not int or entry[k] <= 0 for k in ('width', 'height'))):
            raise ValueError('筛选项目清单包含无效记录')
        used.add(key); ids.add(entry['id'])
        image, label = _paths(root, entry)
        _safe_file(root, image); _safe_file(root, label, False)
    return document


def _signature(session):
    return tuple((item.record_id, item.name, item in session.trash) for item in session.items + session.trash)


def _attach(session, root, document):
    session.project_root = root
    session.origin_root = Path(document['source_root'])
    session.project_id = document['id']
    session.saved_signature = _signature(session)


class WorkspaceSettings:
    def __init__(self, path=None):
        base = os.environ.get('YOLO_BACKPROP_CONFIG_DIR') or Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config') / 'yolo-backprop'
        self.path = Path(path) if path else Path(base) / 'workspace.json'
        self.root = None
        try:
            value = json.loads(self.path.read_text(encoding='utf-8'))['root']
            if isinstance(value, str) and value: self.root = Path(value).expanduser().resolve()
        except (OSError, ValueError, KeyError, TypeError): pass

    def select(self, root):
        workspace = Workspace(root)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        _atomic_json(self.path, {'root': str(workspace.root), 'version': 1})
        self.root = workspace.root
        return workspace


class Workspace:
    def __init__(self, root):
        self.root = Path(root).expanduser().resolve()
        self.project_dir = self.root / 'projects'
        if self.project_dir.is_symlink(): raise ValueError('工作空间 projects 不能是符号链接')
        self.project_dir.mkdir(parents=True, exist_ok=True)

    def projects(self):
        return sorted(p for p in self.project_dir.iterdir() if p.is_dir() and not p.is_symlink()
                      and not p.name.startswith('.') and (p / MARKER).is_file())

    def import_folder(self, root, check_cancelled=lambda: None, progress=lambda *args: None):
        root = Path(root).expanduser().resolve()
        if root.is_relative_to(self.root) or self.root.is_relative_to(root):
            raise ValueError('图片源目录与工作空间不能互相包含，请选择独立的工作空间')
        source = ScreeningSession.scan(root, check_cancelled, progress)
        base = root.name + '_筛选'; destination = self.project_dir / base; counter = 2
        while destination.exists():
            destination = self.project_dir / (base + '_' + str(counter)); counter += 1
        created = False
        try:
            source.export_project(destination, check_cancelled, progress)
            created = True
            session = ScreeningSession.scan(destination / 'images', check_cancelled)
            session.skipped = source.skipped
            document = {'version': 1, 'id': uuid.uuid4().hex, 'source_root': str(root), 'entries': []}
            for item in session.items:
                item.record_id = uuid.uuid4().hex
                document['entries'].append({'id': item.record_id, 'name': item.name, 'width': item.width,
                                            'height': item.height, 'trash': False})
            check_cancelled(); _write_manifest(destination, document)
            _attach(session, destination, document)
            return session
        except BaseException:
            if created: shutil.rmtree(destination)
            raise

    def open_project(self, root):
        path = Path(root).expanduser()
        if path.is_symlink(): raise ValueError('项目不能是符号链接')
        path = path.resolve()
        if path.parent != self.project_dir: raise ValueError('请选择当前工作空间 projects 下的筛选项目')
        document = _read_manifest(path)
        session = ScreeningSession(path / 'images', [], [])
        for entry in document['entries']:
            image, label = _paths(path, entry)
            label = label if label.exists() else None
            item = ScreeningItem(image, entry['name'], entry['width'], entry['height'], _stamp(image),
                                 label, _stamp(label) if label else None, entry['id'])
            (session.trash if entry['trash'] else session.items).append(item)
        _attach(session, path, document)
        return session


def save_project(session, check_cancelled=lambda: None, progress=lambda *args: None, categories=None, purge=False):
    root = session.project_root
    if root is None or root.is_symlink() or root != root.resolve(): raise ValueError('请先导入到工作空间')
    document = _read_manifest(root)
    if document['id'] != session.project_id: raise ValueError('项目已被替换，请重新打开')
    if purge and _signature(session) != session.saved_signature:
        raise ValueError('请先成功保存筛选结果，再确认清理回收站')
    saved = {entry['id']: entry for entry in document['entries']}
    all_items = session.items + session.trash
    if set(saved) != {item.record_id for item in all_items}:
        raise ValueError('项目记录已变化，请重新打开')
    for item in all_items:
        if not _valid_name(item.name) or item.source != _paths(root, saved[item.record_id])[0]:
            raise ValueError('项目记录路径无效')
    stage = Path(tempfile.mkdtemp(prefix='.' + root.name + '-save-', dir=root.parent))
    backup = root.parent / ('.' + root.name + '-backup-' + uuid.uuid4().hex)
    committed = False
    try:
        # Hard links only join owned workspace copies. Staged JSON writes replace their inode.
        def clone(source, target):
            check_cancelled()
            try: return os.link(source, target)
            except OSError: return shutil.copy2(source, target)
        shutil.copytree(root, stage, dirs_exist_ok=True, symlinks=True, copy_function=clone)
        holding = stage / ('.relocate-' + uuid.uuid4().hex); holding.mkdir()
        relocations, entries = [], []
        for index, item in enumerate(all_items):
            check_cancelled()
            old_image, old_label = _paths(root, saved[item.record_id])
            image, label = stage / old_image.relative_to(root), stage / old_label.relative_to(root)
            parked_image = holding / (item.record_id + item.source.suffix)
            image.rename(parked_image)
            parked_label = holding / (item.record_id + '.json')
            if label.exists(): label.rename(parked_label)
            else: parked_label = None
            entry = {'id': item.record_id, 'name': item.name, 'width': item.width,
                     'height': item.height, 'trash': item in session.trash}
            relocations.append((item, entry, parked_image, parked_label))
            progress(index + 1, len(all_items), item.name)
        for item, entry, image, label in relocations:
            check_cancelled()
            if purge and entry['trash']:
                image.unlink()
                if label: label.unlink()
                continue
            target_image, target_label = _paths(stage, entry)
            _safe_file(stage, target_image, False); _safe_file(stage, target_label, False)
            target_image.parent.mkdir(parents=True, exist_ok=True); target_label.parent.mkdir(parents=True, exist_ok=True)
            if target_image.exists() or target_label.exists():
                raise ValueError('存在未登记的同名项目文件，未覆盖：' + item.name)
            image.rename(target_image)
            if label:
                annotation = json.loads(label.read_text(encoding='utf-8'))
                info = annotation.get('info') if isinstance(annotation, dict) else None
                if (not isinstance(info, dict) or info.get('description') != 'ISAT'
                        or info.get('width') != item.width or info.get('height') != item.height
                        or not isinstance(annotation.get('objects'), list)):
                    raise ValueError('标注格式或尺寸不匹配：' + item.name)
                info['name'] = item.name
                info['folder'] = str(_paths(root, entry)[0].parent)
                _atomic_json(target_label, annotation)
            entries.append(entry)
        shutil.rmtree(holding)
        config = stage / 'json' / 'isat.yaml'
        _safe_file(stage, config, False)
        if categories is not None and not config.exists():
            config.parent.mkdir(parents=True, exist_ok=True)
            config.write_text(yaml.safe_dump({'label': categories}, allow_unicode=True), encoding='utf-8')
        document['entries'] = entries
        _write_manifest(stage, document)
        check_cancelled()
        root.rename(backup)
        try: stage.rename(root)
        except BaseException:
            backup.rename(root); raise
        committed = True
        if purge: session.trash.clear()
        for item in session.items + session.trash:
            entry = next(e for e in entries if e['id'] == item.record_id)
            item.source, label = _paths(root, entry)
            item.stamp = _stamp(item.source)
            item.annotation = label if label.exists() else None
            item.annotation_stamp = _stamp(label) if item.annotation else None
        session.saved_signature = _signature(session)
    finally:
        if stage.exists(): shutil.rmtree(stage)
        if committed: shutil.rmtree(backup)
    return {'project_root': str(root), 'image_root': str(root / 'images'),
            'label_root': str(root / 'json'), 'files': [item.name for item in session.items]}


def is_dirty(session):
    return bool(session and session.project_root and _signature(session) != session.saved_signature)
