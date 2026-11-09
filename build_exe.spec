# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec file for YOLO-BACKPROP
# 使用方法: pyinstaller build_exe.spec

import os
from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

block_cipher = None

# 收集所有需要的数据文件
datas = []
binaries = []
hiddenimports = []

# 收集ISAT包的所有数据
datas += collect_data_files('yolo_backprop', include_py_files=True, excludes=['software.yaml', '**/__pycache__/*'])

# 添加图标文件
datas += [('icons', 'icons')]

# 添加配置文件
if os.path.exists('yolo_backprop/categories.yaml'):
    datas += [('yolo_backprop/categories.yaml', 'yolo_backprop')]

# 添加帮助文档
if os.path.exists('yolo_backprop/docs'):
    datas += [('yolo_backprop/docs', 'yolo_backprop/docs')]

# 收集PyQt5相关
tmp_ret = collect_all('PyQt5')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# 收集torch相关
tmp_ret = collect_all('torch')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# 收集torchvision相关
tmp_ret = collect_all('torchvision')
datas += tmp_ret[0]
binaries += tmp_ret[1]
hiddenimports += tmp_ret[2]

# 收集其他关键依赖
for package in ['timm', 'imgviz', 'skimage', 'cv2', 'PIL', 'yaml',
                'pycocotools', 'shapely', 'hydra', 'tqdm',
                'fuzzywuzzy', 'Levenshtein', 'iopath', 'orjson',
                'pydicom', 'requests', 'numpy']:
    try:
        tmp_ret = collect_all(package)
        datas += tmp_ret[0]
        binaries += tmp_ret[1]
        hiddenimports += tmp_ret[2]
    except:
        pass

# 添加隐藏导入
hiddenimports += [
    'yolo_backprop',
    'yolo_backprop.main',
    'yolo_backprop.annotation',
    'yolo_backprop.configs',
    'PIL._tkinter_finder',
    'pkg_resources.py2_warn',
    'sklearn.utils._weight_vector',
    'torchvision.io.image',
]

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['pandas'],  # 排除不需要的大型库（保留matplotlib，因为imgviz需要它）
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='YOLO-BACKPROP',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # 不显示控制台窗口
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='yolo_backprop/yolo-backprop-transparent.ico',
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='YOLO-BACKPROP',
)
