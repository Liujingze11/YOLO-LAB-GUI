# -*- coding: utf-8 -*-
# @Author  : LG

from pathlib import Path

from setuptools import find_packages, setup


def get_version():
    try:
        from yolo_backprop import __version__

        return __version__

    except FileExistsError:
        FileExistsError("yolo_backprop/__init__.py not exists.")


setup(
    name="yolo-backprop",  # 包名
    version=get_version(),  # 版本号
    author="yatengLG",
    author_email="yatenglg@foxmail.com",
    description="Native desktop workbench for image screening, annotation and YOLO model development.",
    long_description=Path(__file__).with_name("README.md").read_text(encoding="utf-8"),
    long_description_content_type="text/markdown",
    url="https://github.com/Liujingze11/YOLO-LAB-GUI",  # 项目相关文件地址
    keywords=[
        "annotation tool",
        "segment anything",
        "image annotation",
        "semantic segmentation",
        "instance segmentation",
    ],
    license="Apache2.0",
    packages=find_packages(),
    include_package_data=True,
    python_requires=">=3.10",  # native model development runtime
    install_requires=[  # 必须直接指明，不然pip包不会自动安装
        "imgviz",
        "scikit-image",
        "numpy",
        "opencv_python_headless",
        "pillow",
        "pyqt5",
        "pyyaml",
        "torch>=2.3.0",
        "torchvision",
        "pycocotools",
        "timm",
        "shapely",
        "hydra-core>=1.3.2",
        "tqdm>=4.66.1",
        "fuzzywuzzy",
        "python-Levenshtein",
        "iopath",
        "orjson",
        "pydicom",
        "requests",
        "einops",
        "psutil",
        "ftfy",
        "regex",
    ],
    extras_require={"yolo": ["ultralytics>=8.0.0", "matplotlib>=3.8"]},
    classifiers=[
        "Intended Audience :: Developers",  # 目标用户:开发者
        "Intended Audience :: Science/Research",  # 目标用户:学者
        "Development Status :: 5 - Production/Stable",
        "Natural Language :: Chinese (Simplified)",
        "Natural Language :: English",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    entry_points={
        "console_scripts": [
            "yolo-backprop=yolo_backprop.main:main",
        ],
        "yolo_backprop.plugins": [],  # 插件注册
    },
)
