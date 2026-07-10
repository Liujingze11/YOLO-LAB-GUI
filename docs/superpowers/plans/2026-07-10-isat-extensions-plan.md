# ISAT 扩展包实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 在不动 `ISAT/` 源码的前提下，新增 `isat_agent_cli` 和 `isat_yolo` 两个独立扩展包，使 AI Agent 能通过 CLI 操控 ISAT 标注流程和 YOLO 训练流水线。

**Architecture:** 两个包各自用 `click` 构建 CLI，`isat_agent_cli` 只读复用 `ISAT.formats.*` 的数据层，`isat_yolo` 封装 `ultralytics.YOLO` 训练引擎 + 参考 YOLO-LAB-GUI 的 TrainConfig/日志/工具逻辑。两包通过 `setup.py` 注册 `console_scripts` 全局可用。

**Tech Stack:** Python 3.10+, click, ultralytics, PyYAML, ISAT.formats (existing)

## Global Constraints

- **零修改**: `ISAT/` 目录下所有文件一字不动
- **无 GUI 依赖**: 不 import PyQt5，不触发 Qt 初始化
- **输出协议**: 所有命令输出 `{"ok": bool, "data": ..., "errors": [...], "warnings": [...]}` 的 JSON 结构，`--format json`(默认) / `table`
- **Python 包命名**: 目录名用下划线 `isat_agent_cli/` `isat_yolo/`，CLI 命令名用连字符 `isat-agent` `isat-yolo`
- **click 框架**: 所有 CLI 入口用 `@click.group()` + `@click.command()` 模式
- **不硬编码两包依赖**: isat_yolo 对 isat_agent_cli 的调用通过 `subprocess` 或 `shutil.which` 检测是否可用

---

## File Structure

```
isat-yolo-lab/
├── ISAT/                       # ★ 不动
├── isat_agent_cli/             # ★ 新建
│   ├── __init__.py
│   ├── cli.py                  # 主 click 入口，注册所有子命令组
│   ├── utils.py                # 输出格式化、JSON 封装、capabilities 注册表
│   └── commands/
│       ├── __init__.py
│       ├── project.py          # project init, info, open
│       ├── category.py         # category list, add, remove, rename, merge
│       ├── convert.py          # 8种格式互转
│       ├── stats.py            # dataset, per-image, category 统计
│       ├── validate.py         # empty, geometry, category, orphan 校验
│       ├── batch.py            # modify-attrs, delete-by-cat, reindex-group
│       ├── media.py            # video2frames, exif-process, dicom-info
│       └── model.py            # list, download, remove
├── isat_yolo/                  # ★ 新建
│   ├── __init__.py
│   ├── cli.py                  # 主 click 入口
│   ├── config.py               # TrainConfig dataclass + merge/save/load
│   ├── logger.py               # CSV 日志 (train_log, result_summary, result_per_class)
│   ├── training.py             # build_train_kwargs, execute_* 训练函数
│   ├── utils.py                # 输出格式化、capabilities
│   └── commands/
│       ├── __init__.py
│       ├── dataset.py          # init, split, balance, yaml
│       ├── train.py            # new, resume, finetune
│       ├── eval.py             # val, summary, per-class
│       ├── log.py              # history, compare, suggest
│       ├── predict.py          # image, batch, video
│       └── config_cmd.py       # show, set
└── setup.py                    # ★ 只追加 entry_points
```

---

## Part A: isat_agent_cli

### Task A1: 包骨架 & 公共工具

**Files:**
- Create: `isat_agent_cli/__init__.py`
- Create: `isat_agent_cli/cli.py`
- Create: `isat_agent_cli/utils.py`
- Create: `isat_agent_cli/commands/__init__.py`

**Produces:**
- `main()` — click 入口函数，供 `setup.py` 引用
- `echo_json(data, ok=True, errors=None, warnings=None)` — 统一 JSON 输出
- `format_output(result, fmt)` — 根据 `--format` 切换 json/table
- `CAPABILITIES` — 全局能力注册字典

- [ ] **Step 1: 创建 `isat_agent_cli/__init__.py`**

```python
"""isat-agent-cli: CLI interface for ISAT annotation tool."""
__version__ = "0.1.0"
```

- [ ] **Step 2: 创建 `isat_agent_cli/utils.py`**

```python
"""Output formatting and capability registry for isat-agent-cli."""
import json
import sys


CAPABILITIES = {
    "package": "isat-agent-cli",
    "version": "0.1.0",
    "description": "CLI interface for ISAT annotation tool",
    "commands": []
}


def register_command(group_name, description, subcommands):
    """Register a command group in the capabilities registry."""
    CAPABILITIES["commands"].append({
        "name": group_name,
        "description": description,
        "subcommands": subcommands
    })


def echo_json(data, ok=True, errors=None, warnings=None):
    """Print unified JSON output to stdout."""
    result = {"ok": ok, "data": data, "errors": errors or [], "warnings": warnings or []}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def format_output(data, fmt, ok=True, errors=None, warnings=None):
    """Dispatch to json or table output based on format flag."""
    if fmt == "json":
        echo_json(data, ok=ok, errors=errors, warnings=warnings)
    else:
        # fallback to JSON for now; table rendering added per-command later
        echo_json(data, ok=ok, errors=errors, warnings=warnings)


def load_project_config(project_dir):
    """Load isat.yaml from project directory. Returns dict or None."""
    import os
    import yaml
    yaml_path = os.path.join(project_dir, "isat.yaml")
    if os.path.exists(yaml_path):
        with open(yaml_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    return None


def save_project_config(project_dir, cfg):
    """Save dict as isat.yaml in project directory."""
    import os
    import yaml
    yaml_path = os.path.join(project_dir, "isat.yaml")
    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(cfg, f, allow_unicode=True, default_flow_style=False)


def count_json_files(directory):
    """Count ISAT json files in a directory."""
    import os
    if not os.path.isdir(directory):
        return 0
    return len([f for f in os.listdir(directory) if f.endswith(".json")])
```

- [ ] **Step 3: 创建 `isat_agent_cli/cli.py`**

```python
"""Main entry point for isat-agent CLI."""
import click

from isat_agent_cli.utils import echo_json, format_output, CAPABILITIES


@click.group()
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json",
              help="Output format (default: json)")
@click.pass_context
def main(ctx, fmt):
    """isat-agent: CLI for ISAT annotation tool.
    
    Use 'isat-agent capabilities' to see all available commands in JSON format.
    """
    ctx.ensure_object(dict)
    ctx.obj["fmt"] = fmt


@main.command()
@click.pass_context
def capabilities(ctx):
    """Output full capabilities manifest as JSON (for AI agent discovery)."""
    # Register commands from all subcommand modules
    from isat_agent_cli.commands.project import register
    register()
    from isat_agent_cli.commands.category import register
    register()
    from isat_agent_cli.commands.convert import register
    register()
    from isat_agent_cli.commands.stats import register
    register()
    from isat_agent_cli.commands.validate import register
    register()
    from isat_agent_cli.commands.batch import register
    register()
    from isat_agent_cli.commands.media import register
    register()
    from isat_agent_cli.commands.model import register
    register()
    echo_json(CAPABILITIES)


# Import and attach subcommand groups
def _register_all():
    from isat_agent_cli.commands.project import project
    main.add_command(project)
    from isat_agent_cli.commands.category import category
    main.add_command(category)
    from isat_agent_cli.commands.convert import convert
    main.add_command(convert)
    from isat_agent_cli.commands.stats import stats
    main.add_command(stats)
    from isat_agent_cli.commands.validate import validate
    main.add_command(validate)
    from isat_agent_cli.commands.batch import batch
    main.add_command(batch)
    from isat_agent_cli.commands.media import media
    main.add_command(media)
    from isat_agent_cli.commands.model import model_cmd
    main.add_command(model_cmd)


_register_all()
```

- [ ] **Step 4: 创建 `isat_agent_cli/commands/__init__.py`**

```python
"""Command modules for isat-agent-cli."""
```

- [ ] **Step 5: 验证骨架可用**

```bash
cd /home/ljz/vibe_coding/YOLO/isat-yolo-lab
python -m isat_agent_cli.cli --help
python -m isat_agent_cli.cli capabilities
```

Expected: `--help` 输出命令树(仅 capabilities), `capabilities` 输出 JSON

- [ ] **Step 6: Commit**

```bash
git add isat_agent_cli/
git commit -m "feat(isat-agent-cli): add package skeleton with utils and capabilities"
```

---

### Task A2: project 命令

**Files:**
- Create: `isat_agent_cli/commands/project.py`

**Interfaces:**
- Produces: `project` click.Group with `init`, `info`, `open` subcommands
- Produces: `register()` function for capabilities

- [ ] **Step 1: 创建 `isat_agent_cli/commands/project.py`**

```python
"""Project management commands."""
import os
import click
from isat_agent_cli.utils import (
    echo_json, format_output, register_command,
    load_project_config, save_project_config, count_json_files
)


def register():
    register_command("project", "项目管理：创建、打开、查看ISAT项目", [
        {"name": "init", "description": "创建新项目", "args": ["--images", "--categories", "--output"]},
        {"name": "info", "description": "查看项目状态", "args": ["--project"]},
        {"name": "open", "description": "验证并打开已有项目", "args": ["--project"]},
    ])


@click.group()
def project():
    """项目管理：创建、打开、查看ISAT项目"""
    pass


@project.command()
@click.option("--images", required=True, type=click.Path(exists=True),
              help="图片目录路径")
@click.option("--categories", required=True,
              help="类别列表，逗号分隔，如: 猫,狗,鸟")
@click.option("--output", default=None, type=click.Path(),
              help="项目输出目录（默认为图片目录）")
@click.pass_context
def init(ctx, images, categories, output):
    """创建新的 ISAT 标注项目。不复制图片，仅创建配置文件和目录结构。"""
    project_dir = output or images
    os.makedirs(project_dir, exist_ok=True)

    cat_list = [c.strip() for c in categories.split(",") if c.strip()]
    if not cat_list:
        echo_json(None, ok=False, errors=["categories 不能为空"])
        return

    # 统计图片
    valid_exts = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".dcm")
    image_files = [
        f for f in sorted(os.listdir(images))
        if f.lower().endswith(valid_exts)
    ]

    # 创建 isat.yaml
    import imgviz
    cmap = imgviz.label_colormap()
    labels = []
    for idx, cat in enumerate(cat_list):
        r, g, b = cmap[idx + 1]
        labels.append({
            "name": cat,
            "color": "#{:02x}{:02x}{:02x}".format(r, g, b)
        })

    cfg = {"label": labels, "image_dir": os.path.abspath(images)}
    save_project_config(project_dir, cfg)

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({
        "project_dir": os.path.abspath(project_dir),
        "images": len(image_files),
        "image_dir": os.path.abspath(images),
        "categories": cat_list,
    }, fmt)


@project.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True),
              help="项目目录路径")
@click.pass_context
def info(ctx, project_dir):
    """查看 ISAT 项目状态：图片数、标注数、类别分布等。"""
    cfg = load_project_config(project_dir)
    categories = []
    if cfg:
        categories = [l["name"] for l in cfg.get("label", [])]

    json_count = count_json_files(project_dir)
    image_dir = cfg.get("image_dir", project_dir) if cfg else project_dir

    # 统计标注信息
    from ISAT.formats.isat import ISAT as ISATFormat
    converter = ISATFormat()
    annotated = 0
    total_objects = 0
    cat_counts = {}

    json_files = [f for f in os.listdir(project_dir) if f.endswith(".json")]
    for jf in json_files:
        try:
            anno = converter.load_one_isat_json(os.path.join(project_dir, jf))
            annotated += 1
            for obj in anno.objs:
                total_objects += 1
                cat_counts[obj.category] = cat_counts.get(obj.category, 0) + 1
        except Exception:
            pass

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({
        "project_dir": os.path.abspath(project_dir),
        "image_dir": os.path.abspath(image_dir),
        "images": json_count,
        "annotated": annotated,
        "unannotated": json_count - annotated,
        "categories": categories,
        "total_objects": total_objects,
        "objects_per_category": cat_counts,
    }, fmt)


@project.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True),
              help="项目目录路径")
@click.pass_context
def open(ctx, project_dir):
    """验证 ISAT 项目完整性并返回路径。AI 可用于确认项目可被 GUI 打开。"""
    cfg = load_project_config(project_dir)
    errors = []
    warnings = []

    if cfg is None:
        errors.append("项目目录中未找到 isat.yaml，请运行 'isat-agent project init' 创建项目")
    else:
        if not cfg.get("label"):
            errors.append("isat.yaml 中没有定义类别 (label)")

    json_count = count_json_files(project_dir)
    if json_count == 0:
        warnings.append("项目中没有 .json 标注文件，是否需要导入图片？")

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({
        "project_dir": os.path.abspath(project_dir),
        "valid": len(errors) == 0,
        "json_files": json_count,
    }, fmt, ok=len(errors) == 0, errors=errors, warnings=warnings)
```

- [ ] **Step 2: 测试 project 命令**

```bash
cd /home/ljz/vibe_coding/YOLO/isat-yolo-lab
# 创建测试项目
mkdir -p /tmp/test-isat-project/images
touch /tmp/test-isat-project/images/img001.jpg
touch /tmp/test-isat-project/images/img002.jpg
python -m isat_agent_cli.cli project init --images /tmp/test-isat-project/images --categories 猫,狗
# 预期: JSON 输出，images=2, categories=["猫","狗"]
python -m isat_agent_cli.cli project info --project /tmp/test-isat-project
# 预期: JSON 输出项目信息
```

Expected: `init` 创建 `isat.yaml`，`info` 统计正确

- [ ] **Step 3: Commit**

```bash
git add isat_agent_cli/commands/project.py
git commit -m "feat(isat-agent-cli): add project init/info/open commands"
```

---

### Task A3: category 命令

**Files:**
- Create: `isat_agent_cli/commands/category.py`

**Interfaces:**
- Consumes: `load_project_config`, `save_project_config`, `echo_json`, `format_output` from `isat_agent_cli.utils`
- Produces: `category` click.Group with `list`, `add`, `remove`, `rename`, `merge` subcommands
- Produces: `register()` function

- [ ] **Step 1: 创建 `isat_agent_cli/commands/category.py`**

```python
"""Category management commands."""
import os
import click
from isat_agent_cli.utils import (
    echo_json, format_output, register_command,
    load_project_config, save_project_config
)


def register():
    register_command("category", "类别管理：查看、添加、删除、重命名、合并类别", [
        {"name": "list", "description": "列出所有类别", "args": ["--project"]},
        {"name": "add", "description": "添加类别", "args": ["--project", "--name", "--color"]},
        {"name": "remove", "description": "删除类别", "args": ["--project", "--name"]},
        {"name": "rename", "description": "重命名类别", "args": ["--project", "--old", "--new"]},
        {"name": "merge", "description": "合并两个类别", "args": ["--project", "--source", "--target"]},
    ])


@click.group()
def category():
    """类别管理：查看、添加、删除、重命名、合并类别"""
    pass


@category.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.pass_context
def list_cmd(ctx, project_dir):
    """列出项目中所有类别。"""
    cfg = load_project_config(project_dir)
    if cfg is None:
        echo_json(None, ok=False, errors=["未找到 isat.yaml"])
        return
    labels = cfg.get("label", [])
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"categories": labels}, fmt)


@category.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.option("--name", required=True, help="类别名称")
@click.option("--color", default=None, help="颜色(hex)，如 #ff0000")
@click.pass_context
def add(ctx, project_dir, name, color):
    """添加新类别到项目。"""
    cfg = load_project_config(project_dir)
    if cfg is None:
        cfg = {"label": []}
    labels = cfg.get("label", [])

    existing = [l["name"] for l in labels]
    if name in existing:
        echo_json(None, ok=False, errors=[f"类别 '{name}' 已存在"])
        return

    import imgviz
    cmap = imgviz.label_colormap()
    idx = len(labels) + 1
    r, g, b = cmap[idx]
    if color:
        r, g, b = int(color[1:3], 16), int(color[3:5], 16), int(color[5:7], 16)

    labels.append({"name": name, "color": "#{:02x}{:02x}{:02x}".format(r, g, b)})
    cfg["label"] = labels
    save_project_config(project_dir, cfg)

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"added": name, "total": len(labels)}, fmt)


@category.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.option("--name", required=True, help="要删除的类别名称")
@click.pass_context
def remove(ctx, project_dir, name):
    """从项目中删除类别（不会删除已有标注数据）。"""
    cfg = load_project_config(project_dir)
    if cfg is None:
        echo_json(None, ok=False, errors=["未找到 isat.yaml"])
        return

    labels = cfg.get("label", [])
    new_labels = [l for l in labels if l["name"] != name]
    if len(new_labels) == len(labels):
        echo_json(None, ok=False, errors=[f"类别 '{name}' 不存在"])
        return

    cfg["label"] = new_labels
    save_project_config(project_dir, cfg)

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"removed": name, "remaining": len(new_labels)}, fmt)


@category.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.option("--old", "old_name", required=True, help="旧类别名称")
@click.option("--new", "new_name", required=True, help="新类别名称")
@click.pass_context
def rename(ctx, project_dir, old_name, new_name):
    """重命名类别，同时更新所有标注文件中的类别名。"""
    cfg = load_project_config(project_dir)
    if cfg is None:
        echo_json(None, ok=False, errors=["未找到 isat.yaml"])
        return

    # 更新 isat.yaml
    labels = cfg.get("label", [])
    found = False
    for l in labels:
        if l["name"] == old_name:
            l["name"] = new_name
            found = True
            break
    if not found:
        echo_json(None, ok=False, errors=[f"类别 '{old_name}' 不存在"])
        return
    save_project_config(project_dir, cfg)

    # 更新所有 json 标注文件
    import json as json_mod
    updated = 0
    for fname in os.listdir(project_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(project_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json_mod.load(f)
        changed = False
        for obj in data.get("objects", []):
            if obj.get("category") == old_name:
                obj["category"] = new_name
                changed = True
        if changed:
            with open(fpath, "w", encoding="utf-8") as f:
                json_mod.dump(data, f, indent=4, ensure_ascii=False)
            updated += 1

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"renamed": f"{old_name} -> {new_name}", "files_updated": updated}, fmt)


@category.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.option("--source", required=True, help="源类别（将被合并到目标）")
@click.option("--target", required=True, help="目标类别（保留）")
@click.pass_context
def merge(ctx, project_dir, source, target):
    """将 source 类别的所有标注合并到 target 类别，并删除 source 类别。"""
    cfg = load_project_config(project_dir)
    if cfg is None:
        echo_json(None, ok=False, errors=["未找到 isat.yaml"])
        return

    labels = cfg.get("label", [])
    names = [l["name"] for l in labels]
    if source not in names:
        echo_json(None, ok=False, errors=[f"源类别 '{source}' 不存在"])
        return
    if target not in names:
        echo_json(None, ok=False, errors=[f"目标类别 '{target}' 不存在"])
        return

    # 更新标注文件
    import json as json_mod
    merged_count = 0
    updated_files = 0
    for fname in os.listdir(project_dir):
        if not fname.endswith(".json"):
            continue
        fpath = os.path.join(project_dir, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            data = json_mod.load(f)
        changed = False
        for obj in data.get("objects", []):
            if obj.get("category") == source:
                obj["category"] = target
                changed = True
                merged_count += 1
        if changed:
            with open(fpath, "w", encoding="utf-8") as f:
                json_mod.dump(data, f, indent=4, ensure_ascii=False)
            updated_files += 1

    # 删除 source 类别
    cfg["label"] = [l for l in labels if l["name"] != source]
    save_project_config(project_dir, cfg)

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({
        "merged": f"{source} -> {target}",
        "objects_merged": merged_count,
        "files_updated": updated_files,
    }, fmt)
```

- [ ] **Step 2: 注册 category 到 cli.py**

```python
# 在 _register_all() 中添加:
from isat_agent_cli.commands.category import category
main.add_command(category)
```

- [ ] **Step 3: 测试**

```bash
python -m isat_agent_cli.cli category list --project /tmp/test-isat-project
python -m isat_agent_cli.cli category add --project /tmp/test-isat-project --name 鸟
python -m isat_agent_cli.cli category rename --project /tmp/test-isat-project --old 鸟 --new 雀
```

- [ ] **Step 4: Commit**

```bash
git add isat_agent_cli/commands/category.py isat_agent_cli/cli.py
git commit -m "feat(isat-agent-cli): add category list/add/remove/rename/merge commands"
```

---

### Task A4: convert 命令

**Files:**
- Create: `isat_agent_cli/commands/convert.py`

**Interfaces:**
- Consumes: `ISAT.formats.yolo.YOLO`, `ISAT.formats.coco.COCO`, `ISAT.formats.labelme.LABELME`, `ISAT.formats.voc.VOC`, `ISAT.formats.voc_detection.VOCDetect`
- Produces: `convert` click.Group with 8 subcommands

- [ ] **Step 1: 创建 `isat_agent_cli/commands/convert.py`**

```python
"""Format conversion commands."""
import os
import click
from isat_agent_cli.utils import echo_json, format_output, register_command


def register():
    register_command("convert", "格式互转：ISAT ↔ YOLO/COCO/Labelme/VOC", [
        {"name": "isat2yolo", "description": "ISAT json → YOLO txt", "args": ["--json-root", "--txt-root", "--ignore-background"]},
        {"name": "yolo2isat", "description": "YOLO txt → ISAT json", "args": ["--images", "--txts", "--out", "--category-file"]},
        {"name": "isat2coco", "description": "ISAT json → COCO json", "args": ["--json-root", "--out"]},
        {"name": "coco2isat", "description": "COCO json → ISAT json", "args": ["--coco-json", "--out"]},
        {"name": "isat2labelme", "description": "ISAT json → Labelme json", "args": ["--json-root", "--out"]},
        {"name": "labelme2isat", "description": "Labelme json → ISAT json", "args": ["--json-root", "--out"]},
        {"name": "isat2voc", "description": "ISAT json → VOC png", "args": ["--json-root", "--out", "--instance", "--use-setting-color"]},
        {"name": "isat2voc-det", "description": "ISAT json → VOC xml (detection)", "args": ["--json-root", "--out"]},
    ])


@click.group()
def convert():
    """格式互转：ISAT ↔ YOLO/COCO/Labelme/VOC"""
    pass


def _do_isat2yolo(json_root, txt_root, ignore_background, fmt):
    from ISAT.formats.yolo import YOLO
    converter = YOLO()
    converter.ignore_background = ignore_background
    converter.read_from_ISAT(json_root)
    converter.save_to_YOLO(txt_root)
    cates = list(converter.cates)
    if ignore_background and "__background__" in cates:
        cates.remove("__background__")
    format_output({
        "json_root": json_root,
        "txt_root": txt_root,
        "converted": len(converter.annos),
        "categories": cates,
    }, fmt)


@convert.command()
@click.option("--json-root", required=True, type=click.Path(exists=True))
@click.option("--txt-root", required=True, type=click.Path())
@click.option("--ignore-background", is_flag=True, help="忽略 __background__ 类别")
@click.pass_context
def isat2yolo(ctx, json_root, txt_root, ignore_background):
    """ISAT json 标注 → YOLO txt 格式"""
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        _do_isat2yolo(json_root, txt_root, ignore_background, fmt)
    except Exception as e:
        echo_json(None, ok=False, errors=[str(e)])


@convert.command()
@click.option("--images", required=True, type=click.Path(exists=True))
@click.option("--txts", required=True, type=click.Path(exists=True))
@click.option("--out", required=True, type=click.Path())
@click.option("--category-file", default=None, type=click.Path(exists=True))
@click.pass_context
def yolo2isat(ctx, images, txts, out, category_file):
    """YOLO txt 标注 → ISAT json 格式"""
    from ISAT.formats.yolo import YOLO
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        converter = YOLO()
        class_dict = None
        if category_file:
            class_dict = {}
            with open(category_file, "r", encoding="utf-8") as f:
                for idx, line in enumerate(f):
                    class_dict[idx] = line.rstrip("\n")
        converter.read_from_YOLO(images, txts, class_dict)
        os.makedirs(out, exist_ok=True)
        converter.save_to_ISAT(out)
        format_output({
            "out": os.path.abspath(out),
            "converted": len(converter.annos),
            "categories": list(converter.cates),
        }, fmt)
    except Exception as e:
        echo_json(None, ok=False, errors=[str(e)])


@convert.command()
@click.option("--json-root", required=True, type=click.Path(exists=True))
@click.option("--out", required=True, type=click.Path())
@click.option("--keep-crowd", is_flag=True, help="保留 crowd 标注")
@click.pass_context
def isat2coco(ctx, json_root, out, keep_crowd):
    """ISAT json 标注 → COCO json 格式"""
    from ISAT.formats.coco import COCO
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        converter = COCO()
        converter.keep_crowd = keep_crowd
        converter.read_from_ISAT(json_root)
        converter.save_to_coco(out, converter.cates)
        format_output({
            "out": os.path.abspath(out),
            "converted": len(converter.annos),
        }, fmt)
    except Exception as e:
        echo_json(None, ok=False, errors=[str(e)])


@convert.command()
@click.option("--coco-json", required=True, type=click.Path(exists=True))
@click.option("--out", required=True, type=click.Path())
@click.option("--keep-crowd", is_flag=True)
@click.pass_context
def coco2isat(ctx, coco_json, out, keep_crowd):
    """COCO json 标注 → ISAT json 格式"""
    from ISAT.formats.coco import COCO
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        converter = COCO()
        converter.keep_crowd = keep_crowd
        converter.read_from_coco(coco_json)
        os.makedirs(out, exist_ok=True)
        converter.save_to_ISAT(out)
        format_output({
            "out": os.path.abspath(out),
            "converted": len(converter.annos),
            "categories": list(converter.cates),
        }, fmt)
    except Exception as e:
        echo_json(None, ok=False, errors=[str(e)])


@convert.command()
@click.option("--json-root", required=True, type=click.Path(exists=True))
@click.option("--out", required=True, type=click.Path())
@click.pass_context
def isat2labelme(ctx, json_root, out):
    """ISAT json 标注 → Labelme json 格式"""
    from ISAT.formats.labelme import LABELME
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        converter = LABELME()
        converter.read_from_ISAT(json_root)
        os.makedirs(out, exist_ok=True)
        converter.save_to_Labelme(out)
        format_output({
            "out": os.path.abspath(out),
            "converted": len(converter.annos),
        }, fmt)
    except Exception as e:
        echo_json(None, ok=False, errors=[str(e)])


@convert.command()
@click.option("--json-root", required=True, type=click.Path(exists=True))
@click.option("--out", required=True, type=click.Path())
@click.pass_context
def labelme2isat(ctx, json_root, out):
    """Labelme json 标注 → ISAT json 格式"""
    from ISAT.formats.labelme import LABELME
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        converter = LABELME()
        converter.read_from_Labelme(json_root)
        os.makedirs(out, exist_ok=True)
        converter.save_to_ISAT(out)
        format_output({
            "out": os.path.abspath(out),
            "converted": len(converter.annos),
            "categories": list(converter.cates),
        }, fmt)
    except Exception as e:
        echo_json(None, ok=False, errors=[str(e)])


@convert.command()
@click.option("--json-root", required=True, type=click.Path(exists=True))
@click.option("--out", required=True, type=click.Path())
@click.option("--instance/--semantic", default=False, help="实例分割 vs 语义分割")
@click.option("--use-setting-color", is_flag=True)
@click.pass_context
def isat2voc(ctx, json_root, out, instance, use_setting_color):
    """ISAT json 标注 → VOC png 格式"""
    from ISAT.formats.voc import VOC
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        converter = VOC()
        converter.is_instance = instance
        converter.use_setting_color = use_setting_color
        converter.read_from_ISAT(json_root)
        os.makedirs(out, exist_ok=True)
        converter.save_to_VOC(out)
        format_output({
            "out": os.path.abspath(out),
            "converted": len(converter.annos),
        }, fmt)
    except Exception as e:
        echo_json(None, ok=False, errors=[str(e)])


@convert.command()
@click.option("--json-root", required=True, type=click.Path(exists=True))
@click.option("--out", required=True, type=click.Path())
@click.pass_context
def isat2voc_det(ctx, json_root, out):
    """ISAT json 标注 → VOC xml 格式（目标检测）"""
    from ISAT.formats.voc_detection import VOCDetect
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        converter = VOCDetect()
        converter.read_from_ISAT(json_root)
        os.makedirs(out, exist_ok=True)
        converter.save_to_VOC_detection(out)
        format_output({
            "out": os.path.abspath(out),
            "converted": len(converter.annos),
        }, fmt)
    except Exception as e:
        echo_json(None, ok=False, errors=[str(e)])


# Alias for CLI name consistency
isat2voc_det = isat2voc_det
```

- [ ] **Step 2: 验证 converter 方法签名**

检查 ISAT.formats 中各 converter 的实际 save 方法名：

```bash
grep -n "def save_to_" /home/ljz/vibe_coding/YOLO/isat-yolo-lab/ISAT/formats/*.py
grep -n "def read_from_" /home/ljz/vibe_coding/YOLO/isat-yolo-lab/ISAT/formats/*.py
```

Expected: 确认方法名正确，如有差异修正 convert.py 中的调用

- [ ] **Step 3: 注册 convert 到 cli.py 并测试**

```bash
python -m isat_agent_cli.cli convert isat2yolo --json-root /tmp/test-isat-project --txt-root /tmp/test-yolo-out
```

- [ ] **Step 4: Commit**

---

### Task A5: stats 命令

**Files:**
- Create: `isat_agent_cli/commands/stats.py`

**Interfaces:**
- Consumes: `ISAT.formats.isat.ISAT`, `echo_json`, `format_output`
- Produces: `stats` click.Group with `dataset`, `per-image`, `category` subcommands

- [ ] **Step 1: 创建 `isat_agent_cli/commands/stats.py`**

```python
"""Dataset statistics commands."""
import os
import click
from isat_agent_cli.utils import echo_json, format_output, register_command


def register():
    register_command("stats", "数据统计：整体统计、逐图统计、逐类别统计", [
        {"name": "dataset", "description": "整体统计", "args": ["--project"]},
        {"name": "per-image", "description": "逐图统计", "args": ["--project"]},
        {"name": "category", "description": "逐类别统计", "args": ["--project"]},
    ])


@click.group()
def stats():
    """数据统计：数据集、图片、类别维度"""
    pass


def _load_annotations(project_dir):
    """Load all ISAT annotations from project directory. Returns list of (name, anno)."""
    from ISAT.formats.isat import ISAT
    converter = ISAT()
    results = []
    for fname in sorted(os.listdir(project_dir)):
        if not fname.endswith(".json"):
            continue
        try:
            anno = converter.load_one_isat_json(os.path.join(project_dir, fname))
            name = os.path.splitext(fname)[0]
            results.append((name, anno))
        except Exception:
            pass
    return results


@stats.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.pass_context
def dataset(ctx, project_dir):
    """整体数据集统计：图片数、标注数、类别数等。"""
    annos = _load_annotations(project_dir)
    total_images = len(annos)
    total_objects = 0
    categories = set()
    group_ids = set()

    for _, anno in annos:
        for obj in anno.objs:
            total_objects += 1
            categories.add(obj.category)
            group_ids.add(obj.group)

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({
        "total_images": total_images,
        "total_objects": total_objects,
        "total_categories": len(categories),
        "categories": sorted(categories),
        "total_groups": len(group_ids),
        "avg_objects_per_image": round(total_objects / total_images, 1) if total_images > 0 else 0,
    }, fmt)


@stats.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.pass_context
def per_image(ctx, project_dir):
    """逐图统计：每张图的标注对象数、类别。"""
    annos = _load_annotations(project_dir)
    results = []
    for name, anno in annos:
        obj_cats = {}
        for obj in anno.objs:
            obj_cats[obj.category] = obj_cats.get(obj.category, 0) + 1
        results.append({
            "name": name,
            "width": anno.info.width,
            "height": anno.info.height,
            "num_objects": len(anno.objs),
            "categories": obj_cats,
        })

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"per_image": results}, fmt)


@stats.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.pass_context
def category(ctx, project_dir):
    """逐类别统计：每个类别的标注数量、出现的图片数。"""
    annos = _load_annotations(project_dir)
    cat_objects = {}
    cat_images = {}

    for _, anno in annos:
        cats_in_image = set()
        for obj in anno.objs:
            cat = obj.category
            cat_objects[cat] = cat_objects.get(cat, 0) + 1
            cats_in_image.add(cat)
        for cat in cats_in_image:
            cat_images[cat] = cat_images.get(cat, 0) + 1

    results = []
    for cat in sorted(cat_objects.keys()):
        results.append({
            "category": cat,
            "objects": cat_objects[cat],
            "images": cat_images.get(cat, 0),
        })

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"per_category": results}, fmt)
```

- [ ] **Step 2: 注册 stats 到 cli.py**

```python
from isat_agent_cli.commands.stats import stats
main.add_command(stats)
```

- [ ] **Step 3: Commit**

---

### Task A6: validate 命令

**Files:**
- Create: `isat_agent_cli/commands/validate.py`

**Interfaces:**
- Consumes: `_load_annotations` pattern from stats.py, `echo_json`, `format_output`
- Produces: `validate` click.Group with `all`, `empty`, `geometry`, `category`, `orphan` subcommands

- [ ] **Step 1: 创建 `isat_agent_cli/commands/validate.py`**

```python
"""Annotation validation commands."""
import os
import click
from isat_agent_cli.utils import (
    echo_json, format_output, register_command,
    load_project_config, count_json_files
)


def register():
    register_command("validate", "标注校验：空标注、几何合法性、类别一致性等", [
        {"name": "all", "description": "运行全部检查", "args": ["--project"]},
        {"name": "empty", "description": "检查空标注", "args": ["--project"]},
        {"name": "geometry", "description": "检查非法多边形", "args": ["--project"]},
        {"name": "category", "description": "检查类别一致性", "args": ["--project"]},
        {"name": "orphan", "description": "检查孤立文件", "args": ["--project"]},
    ])


@click.group()
def validate():
    """标注校验：检查标注数据的完整性和合法性"""
    pass


def _load_annotations(project_dir):
    from ISAT.formats.isat import ISAT
    converter = ISAT()
    results = []
    for fname in sorted(os.listdir(project_dir)):
        if not fname.endswith(".json"):
            continue
        try:
            anno = converter.load_one_isat_json(os.path.join(project_dir, fname))
            name = os.path.splitext(fname)[0]
            results.append((name, anno))
        except Exception as e:
            results.append((os.path.splitext(fname)[0], None))
    return results


def _check_empty(project_dir):
    issues = []
    for name, anno in _load_annotations(project_dir):
        if anno is None:
            continue
        if len(anno.objs) == 0:
            issues.append({
                "file": f"{name}.json",
                "severity": "warning",
                "type": "empty",
                "detail": "标注对象数为0",
            })
    return issues


def _check_geometry(project_dir):
    issues = []
    for name, anno in _load_annotations(project_dir):
        if anno is None:
            continue
        for i, obj in enumerate(anno.objs):
            seg = obj.segmentation
            if not seg or len(seg) < 3:
                issues.append({
                    "file": f"{name}.json",
                    "severity": "error",
                    "type": "geometry",
                    "detail": f"对象#{i} ({obj.category}) 顶点数不足3个: {len(seg)}",
                })
            # Check for self-intersection (simple check: duplicate consecutive points)
            elif len(seg) > 2:
                for j in range(len(seg) - 1):
                    if seg[j] == seg[j + 1]:
                        issues.append({
                            "file": f"{name}.json",
                            "severity": "warning",
                            "type": "geometry",
                            "detail": f"对象#{i} ({obj.category}) 存在重复顶点",
                        })
                        break
    return issues


def _check_category(project_dir):
    issues = []
    cfg = load_project_config(project_dir)
    valid_cats = set()
    if cfg:
        valid_cats = {l["name"] for l in cfg.get("label", [])}

    if not valid_cats:
        return issues  # skip if no category config

    for name, anno in _load_annotations(project_dir):
        if anno is None:
            continue
        for i, obj in enumerate(anno.objs):
            if obj.category not in valid_cats:
                issues.append({
                    "file": f"{name}.json",
                    "severity": "warning",
                    "type": "category",
                    "detail": f"对象#{i} 类别'{obj.category}'不在项目类别列表中",
                })
    return issues


def _check_orphan(project_dir):
    issues = []
    json_names = set()
    for fname in os.listdir(project_dir):
        if fname.endswith(".json"):
            json_names.add(os.path.splitext(fname)[0])

    # Check for json files without corresponding images
    cfg = load_project_config(project_dir)
    image_dir = cfg.get("image_dir", project_dir) if cfg else project_dir

    if os.path.isdir(image_dir):
        valid_exts = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff", ".dcm")
        image_names = set()
        for fname in os.listdir(image_dir):
            if fname.lower().endswith(valid_exts):
                image_names.add(os.path.splitext(fname)[0])

        for jname in json_names:
            if jname not in image_names:
                issues.append({
                    "file": f"{jname}.json",
                    "severity": "warning",
                    "type": "orphan",
                    "detail": f"存在标注文件但无对应图片: {jname}",
                })

    return issues


@validate.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.pass_context
def all_cmd(ctx, project_dir):
    """运行全部校验检查。"""
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    issues = []
    issues += _check_empty(project_dir)
    issues += _check_geometry(project_dir)
    issues += _check_category(project_dir)
    issues += _check_orphan(project_dir)
    severity_counts = {"error": 0, "warning": 0}
    for iss in issues:
        severity_counts[iss["severity"]] = severity_counts.get(iss["severity"], 0) + 1
    format_output({
        "total_issues": len(issues),
        "errors": severity_counts.get("error", 0),
        "warnings": severity_counts.get("warning", 0),
        "issues": issues,
    }, fmt)


@validate.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.pass_context
def empty(ctx, project_dir):
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    issues = _check_empty(project_dir)
    format_output({"issues": issues, "count": len(issues)}, fmt)


@validate.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.pass_context
def geometry(ctx, project_dir):
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    issues = _check_geometry(project_dir)
    format_output({"issues": issues, "count": len(issues)}, fmt)


@validate.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.pass_context
def category(ctx, project_dir):
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    issues = _check_category(project_dir)
    format_output({"issues": issues, "count": len(issues)}, fmt)


@validate.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.pass_context
def orphan(ctx, project_dir):
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    issues = _check_orphan(project_dir)
    format_output({"issues": issues, "count": len(issues)}, fmt)
```

- [ ] **Step 2: 注册 validate 到 cli.py**

```python
from isat_agent_cli.commands.validate import validate
main.add_command(validate)
```

- [ ] **Step 3: Commit**

---

### Task A7: batch 命令

**Files:**
- Create: `isat_agent_cli/commands/batch.py`

**Interfaces:**
- Consumes: `echo_json`, `format_output`, json 文件读写
- Produces: `batch` click.Group with `modify-attrs`, `delete-by-cat`, `reindex-group`

- [ ] **Step 1: 创建 `isat_agent_cli/commands/batch.py`**

```python
"""Batch operation commands."""
import os
import json as json_mod
import click
from isat_agent_cli.utils import echo_json, format_output, register_command


def register():
    register_command("batch", "批量操作：修改属性、按类别删除、重新编排分组", [
        {"name": "modify-attrs", "description": "批量修改多边形属性", "args": ["--project", "--group", "--category", "--iscrowd", "--note"]},
        {"name": "delete-by-cat", "description": "按类别批量删除标注", "args": ["--project", "--category"]},
        {"name": "reindex-group", "description": "重新编排分组编号", "args": ["--project"]},
    ])


@click.group()
def batch():
    """批量操作：批量修改、删除、重新编号"""
    pass


def _iter_json_files(project_dir):
    for fname in sorted(os.listdir(project_dir)):
        if fname.endswith(".json"):
            yield fname, os.path.join(project_dir, fname)


@batch.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.option("--group", type=int, default=None, help="目标 group ID，不指定则匹配所有分组")
@click.option("--category", default=None, help="目标类别名，不指定则匹配所有类别")
@click.option("--iscrowd", type=bool, default=None, help="设置 iscrowd 属性")
@click.option("--note", default=None, help="设置 note 属性")
@click.pass_context
def modify_attrs(ctx, project_dir, group, category, iscrowd, note):
    """批量修改多边形属性。至少指定一个要修改的属性。"""
    if group is None and category is None:
        echo_json(None, ok=False, errors=["至少指定 --group 或 --category 来筛选目标"])
        return
    if iscrowd is None and note is None:
        echo_json(None, ok=False, errors=["至少指定一个要修改的属性: --iscrowd 或 --note"])
        return

    updated_files = 0
    updated_objects = 0

    for fname, fpath in _iter_json_files(project_dir):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json_mod.load(f)
        changed = False
        for obj in data.get("objects", []):
            match = True
            if group is not None and obj.get("group") != group:
                match = False
            if category is not None and obj.get("category") != category:
                match = False
            if match:
                if iscrowd is not None:
                    obj["iscrowd"] = iscrowd
                if note is not None:
                    obj["note"] = note
                changed = True
                updated_objects += 1
        if changed:
            with open(fpath, "w", encoding="utf-8") as f:
                json_mod.dump(data, f, indent=4, ensure_ascii=False)
            updated_files += 1

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"files_updated": updated_files, "objects_updated": updated_objects}, fmt)


@batch.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.option("--category", required=True, help="要删除的类别名")
@click.pass_context
def delete_by_cat(ctx, project_dir, category):
    """按类别批量删除标注对象。"""
    deleted = 0
    updated_files = 0
    for fname, fpath in _iter_json_files(project_dir):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json_mod.load(f)
        old_count = len(data.get("objects", []))
        data["objects"] = [obj for obj in data.get("objects", [])
                           if obj.get("category") != category]
        new_count = len(data["objects"])
        if new_count < old_count:
            with open(fpath, "w", encoding="utf-8") as f:
                json_mod.dump(data, f, indent=4, ensure_ascii=False)
            deleted += (old_count - new_count)
            updated_files += 1

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"deleted_objects": deleted, "files_updated": updated_files}, fmt)


@batch.command()
@click.option("--project", "project_dir", required=True, type=click.Path(exists=True))
@click.pass_context
def reindex_group(ctx, project_dir):
    """按每张图重新编排分组编号（从1开始连续编号）。"""
    updated_files = 0
    for fname, fpath in _iter_json_files(project_dir):
        with open(fpath, "r", encoding="utf-8") as f:
            data = json_mod.load(f)
        objects = data.get("objects", [])
        if not objects:
            continue
        # Collect unique groups preserving order
        groups = []
        seen = set()
        for obj in objects:
            g = obj.get("group", 0)
            if g not in seen:
                groups.append(g)
                seen.add(g)
        if groups == list(range(1, len(groups) + 1)):
            continue  # already indexed from 1
        mapping = {old: new for new, old in enumerate(groups, 1)}
        for obj in objects:
            obj["group"] = mapping.get(obj.get("group", 0), obj.get("group", 0))
        with open(fpath, "w", encoding="utf-8") as f:
            json_mod.dump(data, f, indent=4, ensure_ascii=False)
        updated_files += 1

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"files_updated": updated_files}, fmt)
```

- [ ] **Step 2: 注册并 commit**

---

### Task A8: media 命令

**Files:**
- Create: `isat_agent_cli/commands/media.py`

- [ ] **Step 1: 创建 `isat_agent_cli/commands/media.py`**

```python
"""Media processing commands."""
import os
import click
from isat_agent_cli.utils import echo_json, format_output, register_command


def register():
    register_command("media", "媒体处理：视频抽帧、EXIF处理、DICOM信息", [
        {"name": "video2frames", "description": "视频抽帧", "args": ["--video", "--out", "--fps"]},
        {"name": "exif-process", "description": "处理照片EXIF", "args": ["--dir"]},
        {"name": "dicom-info", "description": "查看DICOM元数据", "args": ["--file"]},
    ])


@click.group()
def media():
    """媒体处理：视频、EXIF、DICOM"""
    pass


@media.command()
@click.option("--video", required=True, type=click.Path(exists=True))
@click.option("--out", required=True, type=click.Path())
@click.option("--fps", type=float, default=None, help="抽帧率(帧/秒)，默认提取所有帧")
@click.pass_context
def video2frames(ctx, video, out, fps):
    """视频抽帧为图片序列。"""
    try:
        import cv2
    except ImportError:
        echo_json(None, ok=False, errors=["需要安装 opencv-python: pip install opencv-python"])
        return

    os.makedirs(out, exist_ok=True)
    cap = cv2.VideoCapture(video)
    video_fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    step = 1
    if fps and fps < video_fps:
        step = int(video_fps / fps)

    saved = 0
    frame_idx = 0
    while True:
        ret, frame = cap.read()
        if not ret:
            break
        if frame_idx % step == 0:
            out_path = os.path.join(out, f"frame_{saved:06d}.jpg")
            cv2.imwrite(out_path, frame)
            saved += 1
        frame_idx += 1
    cap.release()

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({
        "video": video,
        "video_fps": video_fps,
        "total_frames": total_frames,
        "extracted_frames": saved,
        "output_dir": os.path.abspath(out),
    }, fmt)


@media.command()
@click.option("--dir", "directory", required=True, type=click.Path(exists=True))
@click.pass_context
def exif_process(ctx, directory):
    """处理目录中照片的 EXIF 信息（旋转修正）。"""
    try:
        from PIL import Image, ExifTags
    except ImportError:
        echo_json(None, ok=False, errors=["需要安装 Pillow: pip install Pillow"])
        return

    processed = 0
    for fname in os.listdir(directory):
        fpath = os.path.join(directory, fname)
        try:
            img = Image.open(fpath)
            exif = img._getexif()
            if exif:
                orientation = None
                for tag, value in exif.items():
                    if ExifTags.TAGS.get(tag) == "Orientation":
                        orientation = value
                        break
                if orientation == 3:
                    img = img.rotate(180, expand=True)
                elif orientation == 6:
                    img = img.rotate(270, expand=True)
                elif orientation == 8:
                    img = img.rotate(90, expand=True)
                if orientation in (3, 6, 8):
                    img.save(fpath)
                    processed += 1
        except Exception:
            pass

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"directory": directory, "rotated": processed}, fmt)


@media.command()
@click.option("--file", "filepath", required=True, type=click.Path(exists=True))
@click.pass_context
def dicom_info(ctx, filepath):
    """查看 DICOM 文件元数据。"""
    try:
        import pydicom
    except ImportError:
        echo_json(None, ok=False, errors=["需要安装 pydicom: pip install pydicom"])
        return

    ds = pydicom.dcmread(filepath)
    info = {
        "PatientName": str(ds.PatientName) if hasattr(ds, "PatientName") else "N/A",
        "PatientID": ds.PatientID if hasattr(ds, "PatientID") else "N/A",
        "Modality": ds.Modality if hasattr(ds, "Modality") else "N/A",
        "StudyDate": ds.StudyDate if hasattr(ds, "StudyDate") else "N/A",
        "Rows": ds.Rows if hasattr(ds, "Rows") else 0,
        "Columns": ds.Columns if hasattr(ds, "Columns") else 0,
        "PixelSpacing": str(ds.PixelSpacing) if hasattr(ds, "PixelSpacing") else "N/A",
    }

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"file": filepath, "metadata": info}, fmt)
```

- [ ] **Step 2: 注册并 commit**

---

### Task A9: model 命令

**Files:**
- Create: `isat_agent_cli/commands/model.py`

- [ ] **Step 1: 创建 `isat_agent_cli/commands/model.py`**

```python
"""SAM model management commands."""
import os
import click
from isat_agent_cli.utils import echo_json, format_output, register_command
from ISAT.configs import CHECKPOINT_PATH


def register():
    register_command("model", "SAM模型管理：列出、下载、删除模型", [
        {"name": "list", "description": "列出已安装模型", "args": []},
        {"name": "download", "description": "下载模型", "args": ["--name"]},
        {"name": "remove", "description": "删除模型", "args": ["--name"]},
    ])


@click.group("model")
def model_cmd():
    """SAM 模型管理：列出、下载、删除模型文件"""
    pass


@model_cmd.command("list")
@click.pass_context
def list_models(ctx):
    """列出已下载的 SAM 模型。"""
    models = []
    if os.path.isdir(CHECKPOINT_PATH):
        for fname in os.listdir(CHECKPOINT_PATH):
            fpath = os.path.join(CHECKPOINT_PATH, fname)
            if os.path.isfile(fpath) and fname.endswith((".pth", ".pt")):
                size_mb = round(os.path.getsize(fpath) / (1024 * 1024), 1)
                models.append({"name": fname, "size_mb": size_mb, "path": fpath})

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"checkpoint_dir": CHECKPOINT_PATH, "models": models}, fmt)


@model_cmd.command("download")
@click.option("--name", required=True, help="模型名称 (如 sam_vit_h_4b8939.pth)")
@click.pass_context
def download(ctx, name):
    """下载 SAM 模型到 checkpoints 目录。需要网络连接。"""
    os.makedirs(CHECKPOINT_PATH, exist_ok=True)
    target = os.path.join(CHECKPOINT_PATH, name)
    if os.path.exists(target):
        echo_json(None, ok=False, errors=[f"模型 {name} 已存在: {target}"])
        return

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({
        "status": "manual_download_required",
        "name": name,
        "target": target,
        "hint": "SAM 模型需手动下载。请访问 https://github.com/facebookresearch/segment-anything 获取下载链接，将 .pth 文件放入 checkpoints 目录。",
    }, fmt)


@model_cmd.command("remove")
@click.option("--name", required=True, help="要删除的模型名称")
@click.pass_context
def remove(ctx, name):
    """删除已下载的 SAM 模型文件。"""
    target = os.path.join(CHECKPOINT_PATH, name)
    if not os.path.exists(target):
        echo_json(None, ok=False, errors=[f"模型 {name} 不存在"])
        return

    os.remove(target)
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"removed": name, "path": target}, fmt)
```

- [ ] **Step 2: 注册 model_cmd 到 cli.py**

```python
from isat_agent_cli.commands.model import model_cmd
main.add_command(model_cmd)
```

- [ ] **Step 3: Commit**

---

### Task A10: isat-agent-cli 集成测试

- [ ] **Step 1: 端到端测试**

```bash
cd /home/ljz/vibe_coding/YOLO/isat-yolo-lab

# Test capabilities
python -m isat_agent_cli.cli capabilities | python -m json.tool

# Test project workflow
rm -rf /tmp/isat-test
python -m isat_agent_cli.cli project init --images /tmp/test-isat-project/images --categories 猫,狗 --output /tmp/isat-test
python -m isat_agent_cli.cli category add --project /tmp/isat-test --name 鸟
python -m isat_agent_cli.cli category list --project /tmp/isat-test
python -m isat_agent_cli.cli project info --project /tmp/isat-test

# Test validate
python -m isat_agent_cli.cli validate all --project /tmp/isat-test

# All commands should return valid JSON with "ok" field
```

- [ ] **Step 2: 检查无 GUI 依赖**

```bash
# Verify no PyQt5 imports in isat_agent_cli
grep -r "PyQt5\|pyqt5\|QtWidgets\|QtCore\|QtGui" isat_agent_cli/ --include="*.py" || echo "OK: No Qt imports found"
```

- [ ] **Step 3: Commit**

---

## Part B: isat_yolo

### Task B1: 包骨架 & TrainConfig

**Files:**
- Create: `isat_yolo/__init__.py`
- Create: `isat_yolo/cli.py`
- Create: `isat_yolo/config.py`
- Create: `isat_yolo/utils.py`
- Create: `isat_yolo/commands/__init__.py`

**Produces:**
- `TrainConfig` dataclass with merge logic (from YOLO-LAB-GUI `core/config.py`)
- `main()` click entry
- `echo_json`, `format_output`, `CAPABILITIES`

- [ ] **Step 1: 创建 `isat_yolo/__init__.py`**

```python
"""isat-yolo: YOLO training pipeline CLI."""
__version__ = "0.1.0"
```

- [ ] **Step 2: 创建 `isat_yolo/config.py`**

```python
"""TrainConfig dataclass and configuration management."""
import os
import yaml
from dataclasses import dataclass, field, asdict
from pathlib import Path


def _get_default_device():
    import torch
    if torch.cuda.is_available():
        return "cuda"
    elif hasattr(torch.backends, "mps") and torch.backends.mps.is_available():
        return "mps"
    return "cpu"


@dataclass
class TrainConfig:
    # Paths
    data_yaml: str = ""
    model_file: str = ""
    results_dir: str = "./runs"
    log_dir: str = "./logs"

    # Hyperparameters
    epochs: int = 150
    imgsz: int = 640
    batch: int = 16
    device: str = field(default_factory=_get_default_device)
    lr0: float = 0.0005
    close_mosaic: int = 10
    multi_scale: float = 0.5

    experiment_name: str = "experiment"

    # Augmentation switch
    use_augment: bool = True

    # Augmentation params
    hsv_h: float = 0.015
    hsv_s: float = 0.7
    hsv_v: float = 0.4
    degrees: float = 0.0
    translate: float = 0.1
    scale: float = 0.5
    shear: float = 0.0
    perspective: float = 0.0
    flipud: float = 0.0
    fliplr: float = 0.5
    mosaic: float = 1.0
    mixup: float = 0.0
    copy_paste: float = 0.0

    @property
    def save_dir(self) -> str:
        return os.path.join(self.results_dir, self.experiment_name)

    @property
    def last_pt(self) -> str:
        return os.path.join(self.save_dir, "weights", "last.pt")

    @property
    def best_pt(self) -> str:
        return os.path.join(self.save_dir, "weights", "best.pt")


_USER_CONFIG_DIR = Path.home() / ".yolo-lab"
_USER_CONFIG_PATH = _USER_CONFIG_DIR / "config.yaml"


def load_user_config() -> dict | None:
    if not _USER_CONFIG_PATH.is_file():
        return None
    try:
        with open(_USER_CONFIG_PATH, "r", encoding="utf-8") as f:
            return yaml.safe_load(f)
    except Exception:
        return None


def save_user_config(cfg: TrainConfig) -> None:
    _USER_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    d = {k: v for k, v in asdict(cfg).items() if not k.startswith("_")}
    with open(_USER_CONFIG_PATH, "w", encoding="utf-8") as f:
        yaml.dump(d, f, allow_unicode=True, default_flow_style=False)


def merge_config(base: TrainConfig, overrides: dict) -> TrainConfig:
    d = asdict(base)
    for k, v in overrides.items():
        if v is not None and k in d:
            d[k] = v
    return TrainConfig(**d)


def load_effective_config(cli_overrides: dict | None = None) -> TrainConfig:
    cfg = TrainConfig()
    file_cfg = load_user_config()
    if file_cfg:
        cfg = merge_config(cfg, file_cfg)
    if cli_overrides:
        cfg = merge_config(cfg, cli_overrides)
    return cfg


def add_train_options(f):
    """Decorator to add all training-related click options."""
    options = [
        click.option("--epochs", type=int, default=None),
        click.option("--imgsz", type=int, default=None),
        click.option("--batch", type=int, default=None),
        click.option("--device", type=str, default=None),
        click.option("--lr0", type=float, default=None),
        click.option("--close-mosaic", type=int, default=None),
        click.option("--multi-scale", type=float, default=None),
        click.option("--name", "experiment_name", type=str, default=None),
        click.option("--augment/--no-augment", "use_augment", default=None),
    ]
    for opt in reversed(options):
        f = opt(f)
    return f


def build_train_kwargs(config: TrainConfig) -> dict:
    kwargs = {
        "data": config.data_yaml,
        "epochs": config.epochs,
        "imgsz": config.imgsz,
        "batch": config.batch,
        "device": config.device,
        "project": config.results_dir,
        "name": config.experiment_name,
        "exist_ok": True,
        "plots": True,
        "lr0": config.lr0,
        "close_mosaic": config.close_mosaic,
        "multi_scale": config.multi_scale,
    }
    if config.use_augment:
        kwargs.update({
            "hsv_h": config.hsv_h, "hsv_s": config.hsv_s, "hsv_v": config.hsv_v,
            "degrees": config.degrees, "translate": config.translate,
            "scale": config.scale, "shear": config.shear,
            "perspective": config.perspective, "flipud": config.flipud,
            "fliplr": config.fliplr, "mosaic": config.mosaic,
            "mixup": config.mixup, "copy_paste": config.copy_paste,
        })
    return kwargs
```

- [ ] **Step 3: 创建 `isat_yolo/utils.py`**

```python
"""Output utilities for isat-yolo."""
import json
import sys

CAPABILITIES = {
    "package": "isat-yolo",
    "version": "0.1.0",
    "description": "YOLO training pipeline CLI",
    "commands": []
}


def register_command(group_name, description, subcommands):
    CAPABILITIES["commands"].append({
        "name": group_name, "description": description, "subcommands": subcommands
    })


def echo_json(data, ok=True, errors=None, warnings=None):
    result = {"ok": ok, "data": data, "errors": errors or [], "warnings": warnings or []}
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")


def format_output(data, fmt, ok=True, errors=None, warnings=None):
    echo_json(data, ok=ok, errors=errors, warnings=warnings)
```

- [ ] **Step 4: 创建 `isat_yolo/cli.py`**

```python
"""Main entry point for isat-yolo CLI."""
import click
from isat_yolo.utils import echo_json, format_output, CAPABILITIES


@click.group()
@click.option("--format", "fmt", type=click.Choice(["json", "table"]), default="json")
@click.pass_context
def main(ctx, fmt):
    """isat-yolo: YOLO training pipeline CLI."""
    ctx.ensure_object(dict)
    ctx.obj["fmt"] = fmt


@main.command()
@click.pass_context
def capabilities(ctx):
    """Output full capabilities manifest (for AI agent discovery)."""
    from isat_yolo.commands.dataset import register; register()
    from isat_yolo.commands.train import register; register()
    from isat_yolo.commands.eval import register; register()
    from isat_yolo.commands.log import register; register()
    from isat_yolo.commands.predict import register; register()
    from isat_yolo.commands.config_cmd import register; register()
    echo_json(CAPABILITIES)


def _register_all():
    from isat_yolo.commands.dataset import dataset; main.add_command(dataset)
    from isat_yolo.commands.train import train; main.add_command(train)
    from isat_yolo.commands.eval import eval_cmd; main.add_command(eval_cmd)
    from isat_yolo.commands.log import log; main.add_command(log)
    from isat_yolo.commands.predict import predict; main.add_command(predict)
    from isat_yolo.commands.config_cmd import config; main.add_command(config)


_register_all()
```

- [ ] **Step 5: 创建 `isat_yolo/commands/__init__.py`**

```python
"""Command modules for isat-yolo."""
```

- [ ] **Step 6: Commit**

---

### Task B2: dataset 命令

**Files:**
- Create: `isat_yolo/commands/dataset.py`

- [ ] **Step 1: 创建 `isat_yolo/commands/dataset.py`**

```python
"""Dataset preparation commands."""
import os
import shutil
import random
import yaml
import click
from isat_yolo.utils import echo_json, format_output, register_command


def register():
    register_command("dataset", "数据准备：初始化、拆分、平衡分析、生成yaml", [
        {"name": "init", "args": ["--json-root", "--images", "--out"]},
        {"name": "split", "args": ["--dataset", "--mode", "--val-ratio", "--include-test", "--test-ratio"]},
        {"name": "balance", "args": ["--dataset"]},
        {"name": "yaml", "args": ["--dataset", "--names", "--path"]},
    ])


@click.group()
def dataset():
    """数据准备：从标注到可训练数据集"""
    pass


@dataset.command()
@click.option("--json-root", required=True, type=click.Path(exists=True))
@click.option("--images", required=True, type=click.Path(exists=True))
@click.option("--out", required=True, type=click.Path())
@click.pass_context
def init(ctx, json_root, images, out):
    """从 ISAT 标注 + 图片生成 YOLO 格式数据集。"""
    from ISAT.formats.yolo import YOLO

    # Convert ISAT -> YOLO txt
    converter = YOLO()
    converter.read_from_ISAT(json_root)

    # Create dataset structure
    images_dir = os.path.join(out, "images", "train")
    labels_dir = os.path.join(out, "labels", "train")
    os.makedirs(images_dir, exist_ok=True)
    os.makedirs(labels_dir, exist_ok=True)

    # Copy/symlink images and save labels
    valid_exts = (".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff")
    copied = 0
    for name, anno in converter.annos.items():
        img_name = anno.info.name
        src_img = os.path.join(images, img_name)
        if os.path.exists(src_img):
            shutil.copy2(src_img, os.path.join(images_dir, img_name))
            copied += 1
        else:
            # Try with common extensions
            for ext in valid_exts:
                src_img = os.path.join(images, name + ext)
                if os.path.exists(src_img):
                    shutil.copy2(src_img, os.path.join(images_dir, img_name if img_name else name + ext))
                    copied += 1
                    break

    converter.save_to_YOLO(labels_dir)

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({
        "out": os.path.abspath(out),
        "images_copied": copied,
        "labels_created": len(converter.annos),
        "categories": list(converter.cates),
        "structure": {"images/train": images_dir, "labels/train": labels_dir}
    }, fmt)


@dataset.command()
@click.option("--dataset", "dataset_dir", required=True, type=click.Path(exists=True))
@click.option("--mode", type=click.Choice(["random", "every-nth"]), default="random")
@click.option("--val-ratio", type=float, default=0.2)
@click.option("--include-test", is_flag=True)
@click.option("--test-ratio", type=float, default=0.1)
@click.pass_context
def split(ctx, dataset_dir, mode, val_ratio, include_test, test_ratio):
    """拆分数据集为 train/val(/test)。"""
    images_train = os.path.join(dataset_dir, "images", "train")
    labels_train = os.path.join(dataset_dir, "labels", "train")

    if not os.path.isdir(images_train):
        echo_json(None, ok=False, errors=[f"未找到 {images_train}"])
        return

    valid_exts = (".jpg", ".jpeg", ".png")
    all_images = sorted([
        f for f in os.listdir(images_train)
        if f.lower().endswith(valid_exts)
    ])

    if mode == "random":
        random.seed(42)
        random.shuffle(all_images)
        val_n = round(len(all_images) * val_ratio)
        test_n = round(len(all_images) * test_ratio) if include_test else 0
        val_images = all_images[:val_n]
        test_images = all_images[val_n:val_n + test_n] if include_test else []
        train_images = all_images[val_n + test_n:]
    else:  # every-nth
        n = max(2, int(1 / val_ratio))
        val_images = all_images[::n]
        train_images = [img for i, img in enumerate(all_images) if i % n != 0]
        test_images = []

    def _move_files(img_list, src_img_dir, src_lbl_dir, dst_img_dir, dst_lbl_dir):
        os.makedirs(dst_img_dir, exist_ok=True)
        os.makedirs(dst_lbl_dir, exist_ok=True)
        for img in img_list:
            shutil.move(os.path.join(src_img_dir, img), os.path.join(dst_img_dir, img))
            lbl = os.path.splitext(img)[0] + ".txt"
            lbl_src = os.path.join(src_lbl_dir, lbl)
            if os.path.exists(lbl_src):
                shutil.move(lbl_src, os.path.join(dst_lbl_dir, lbl))

    images_val_dir = os.path.join(dataset_dir, "images", "val")
    labels_val_dir = os.path.join(dataset_dir, "labels", "val")
    _move_files(val_images, images_train, labels_train, images_val_dir, labels_val_dir)

    if test_images:
        images_test_dir = os.path.join(dataset_dir, "images", "test")
        labels_test_dir = os.path.join(dataset_dir, "labels", "test")
        _move_files(test_images, images_train, labels_train, images_test_dir, labels_test_dir)

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({
        "train": len(train_images),
        "val": len(val_images),
        "test": len(test_images) if include_test else 0,
        "dataset_dir": os.path.abspath(dataset_dir),
    }, fmt)


@dataset.command()
@click.option("--dataset", "dataset_dir", required=True, type=click.Path(exists=True))
@click.pass_context
def balance(ctx, dataset_dir):
    """分析数据集中各类别的分布平衡情况。"""
    labels_dir = os.path.join(dataset_dir, "labels", "train")
    if not os.path.isdir(labels_dir):
        echo_json(None, ok=False, errors=[f"未找到 {labels_dir}"])
        return

    # Try to load class names
    class_names = {}
    yaml_path = os.path.join(dataset_dir, "data.yaml")
    if os.path.exists(yaml_path):
        with open(yaml_path, "r") as f:
            data = yaml.safe_load(f)
        names = data.get("names", {})
        if isinstance(names, list):
            class_names = {i: n for i, n in enumerate(names)}
        elif isinstance(names, dict):
            class_names = {int(k): v for k, v in names.items()}

    cat_counts = {}
    for fname in os.listdir(labels_dir):
        if not fname.endswith(".txt"):
            continue
        with open(os.path.join(labels_dir, fname), "r") as f:
            for line in f:
                parts = line.strip().split()
                if parts:
                    try:
                        cls_id = int(float(parts[0]))
                        cat_counts[cls_id] = cat_counts.get(cls_id, 0) + 1
                    except ValueError:
                        pass

    if not cat_counts:
        echo_json(None, ok=False, errors=["未找到任何标注数据"])
        return

    total = sum(cat_counts.values())
    avg = total / len(cat_counts)
    results = []
    for cls_id in sorted(cat_counts.keys()):
        count = cat_counts[cls_id]
        ratio = count / avg
        if ratio < 0.3:
            status = "few"
            suggestion = f"建议增加数据或使用增强"
        elif ratio > 3.0:
            status = "many"
            suggestion = f"实例较多({count})，可能不需特别关注"
        else:
            status = "ok"
            suggestion = "分布合理"
        name = class_names.get(cls_id, f"class_{cls_id}")
        results.append({
            "class_id": cls_id, "class_name": name,
            "count": count, "ratio_to_avg": round(ratio, 2),
            "status": status, "suggestion": suggestion,
        })

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"total_instances": total, "num_classes": len(cat_counts),
                   "avg_per_class": round(avg, 1), "per_class": results}, fmt)


@dataset.command()
@click.option("--dataset", "dataset_dir", required=True, type=click.Path(exists=True))
@click.option("--names", default=None, help="类别名称，逗号分隔")
@click.option("--path", "data_path", default=".", help="数据集根路径（相对或绝对）")
@click.pass_context
def yaml_cmd(ctx, dataset_dir, names, data_path):
    """生成或更新 data.yaml 配置文件。"""
    yaml_path = os.path.join(dataset_dir, "data.yaml")
    if names:
        name_list = [n.strip() for n in names.split(",")]
    else:
        # Try to auto-detect from labels
        name_list = []
        labels_dir = os.path.join(dataset_dir, "labels", "train")
        if os.path.isdir(labels_dir):
            max_id = -1
            for fname in os.listdir(labels_dir):
                if fname.endswith(".txt"):
                    with open(os.path.join(labels_dir, fname), "r") as f:
                        for line in f:
                            parts = line.strip().split()
                            if parts:
                                try:
                                    max_id = max(max_id, int(float(parts[0])))
                                except ValueError:
                                    pass
            name_list = [f"class_{i}" for i in range(max_id + 1)]

    config = {
        "path": os.path.abspath(data_path),
        "train": "images/train",
        "val": "images/val",
        "names": {i: name for i, name in enumerate(name_list)},
    }

    # Add test if exists
    if os.path.isdir(os.path.join(dataset_dir, "images", "test")):
        config["test"] = "images/test"

    with open(yaml_path, "w", encoding="utf-8") as f:
        yaml.dump(config, f, allow_unicode=True, default_flow_style=False)

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"yaml_path": yaml_path, "config": config}, fmt)
```

- [ ] **Step 2: 注册并 commit**

---

### Task B3: train 命令

**Files:**
- Create: `isat_yolo/commands/train.py`
- Create: `isat_yolo/training.py`

**Produces:**
- `train` click.Group with `new`, `resume`, `finetune`
- `build_train_kwargs(config)` in `isat_yolo/training.py`

- [ ] **Step 1: 创建 `isat_yolo/training.py`**

```python
"""Training execution functions."""
import os
from isat_yolo.config import TrainConfig, build_train_kwargs


def execute_new_training(config: TrainConfig) -> None:
    from ultralytics import YOLO
    model = YOLO(config.model_file)
    kwargs = build_train_kwargs(config)
    model.train(**kwargs)


def execute_resume_training(config: TrainConfig) -> None:
    from ultralytics import YOLO
    if not os.path.exists(config.last_pt):
        raise FileNotFoundError(f"last.pt not found: {config.last_pt}")
    model = YOLO(config.last_pt)
    model.train(resume=True)


def execute_finetune_training(config: TrainConfig, best_pt_path: str) -> None:
    from ultralytics import YOLO
    if not os.path.exists(best_pt_path):
        raise FileNotFoundError(f"best.pt not found: {best_pt_path}")
    model = YOLO(best_pt_path)
    kwargs = build_train_kwargs(config)
    model.train(**kwargs)
```

- [ ] **Step 2: 创建 `isat_yolo/commands/train.py`**

```python
"""Training commands."""
import os
import click
from isat_yolo.config import TrainConfig, load_effective_config, merge_config, add_train_options
from isat_yolo.training import execute_new_training, execute_resume_training, execute_finetune_training
from isat_yolo.logger import append_train_log
from isat_yolo.utils import echo_json, format_output, register_command


def register():
    register_command("train", "训练：全新训练、恢复训练、微调", [
        {"name": "new", "args": ["--data", "--model", "...训练超参"]},
        {"name": "resume", "args": ["--data", "--last-pt"]},
        {"name": "finetune", "args": ["--data", "--best-pt", "...训练超参"]},
    ])


@click.group()
def train():
    """训练管理：新训练、恢复、微调"""
    pass


def _collect_cli_overrides(ctx):
    """Extract training-related params from click context."""
    params = ctx.params if hasattr(ctx, "params") else {}
    allowed = {"epochs", "imgsz", "batch", "device", "lr0", "close_mosaic",
               "multi_scale", "experiment_name", "use_augment"}
    return {k: v for k, v in params.items() if k in allowed and v is not None}


@train.command()
@click.option("--data", "data_yaml", required=True, type=click.Path(exists=True))
@click.option("--model", "model_file", required=True, type=click.Path(exists=True))
@click.option("--results-dir", default="./runs", type=click.Path())
@click.option("--log-dir", default="./logs", type=click.Path())
@add_train_options
@click.pass_context
def new(ctx, data_yaml, model_file, results_dir, log_dir, **kwargs):
    """全新训练。"""
    overrides = _collect_cli_overrides(ctx)
    overrides["data_yaml"] = data_yaml
    overrides["model_file"] = model_file
    overrides["results_dir"] = results_dir
    overrides["log_dir"] = log_dir

    cfg = load_effective_config(overrides)
    append_train_log(cfg, mode="new_train", status="started")

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        execute_new_training(cfg)
        append_train_log(cfg, mode="new_train", status="finished")
        format_output({"status": "finished", "experiment": cfg.experiment_name,
                       "save_dir": cfg.save_dir, "best_pt": cfg.best_pt}, fmt)
    except Exception as e:
        append_train_log(cfg, mode="new_train", status="failed", notes=str(e))
        echo_json(None, ok=False, errors=[str(e)])


@train.command()
@click.option("--data", "data_yaml", required=True, type=click.Path(exists=True))
@click.option("--last-pt", required=True, type=click.Path(exists=True))
@click.option("--results-dir", default="./runs", type=click.Path())
@click.option("--log-dir", default="./logs", type=click.Path())
@click.option("--name", "experiment_name", default=None)
@click.pass_context
def resume(ctx, data_yaml, last_pt, results_dir, log_dir, experiment_name):
    """从 last.pt 恢复训练。"""
    exp_name = experiment_name or os.path.basename(os.path.dirname(os.path.dirname(last_pt)))
    cfg = TrainConfig(data_yaml=data_yaml, model_file="", results_dir=results_dir,
                      log_dir=log_dir, experiment_name=exp_name)
    append_train_log(cfg, mode="resume_train", status="started")

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        execute_resume_training(cfg)
        append_train_log(cfg, mode="resume_train", status="finished")
        format_output({"status": "finished", "experiment": cfg.experiment_name}, fmt)
    except Exception as e:
        append_train_log(cfg, mode="resume_train", status="failed", notes=str(e))
        echo_json(None, ok=False, errors=[str(e)])


@train.command()
@click.option("--data", "data_yaml", required=True, type=click.Path(exists=True))
@click.option("--best-pt", required=True, type=click.Path(exists=True))
@click.option("--results-dir", default="./runs", type=click.Path())
@click.option("--log-dir", default="./logs", type=click.Path())
@add_train_options
@click.pass_context
def finetune(ctx, data_yaml, best_pt, results_dir, log_dir, **kwargs):
    """从已有 best.pt 微调。"""
    overrides = _collect_cli_overrides(ctx)
    overrides["data_yaml"] = data_yaml
    overrides["model_file"] = ""
    overrides["results_dir"] = results_dir
    overrides["log_dir"] = log_dir

    cfg = load_effective_config(overrides)
    append_train_log(cfg, mode="train_from_best", status="started")

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        execute_finetune_training(cfg, best_pt)
        append_train_log(cfg, mode="train_from_best", status="finished")
        format_output({"status": "finished", "experiment": cfg.experiment_name,
                       "best_pt": cfg.best_pt}, fmt)
    except Exception as e:
        append_train_log(cfg, mode="train_from_best", status="failed", notes=str(e))
        echo_json(None, ok=False, errors=[str(e)])
```

- [ ] **Step 3: Commit**


### Task B4: eval 命令

**Files:**
- Create: `isat_yolo/commands/eval.py`

- [ ] **Step 1: 创建 `isat_yolo/commands/eval.py`**

```python
"""Evaluation commands."""
import os
import csv
import shutil
import click
from isat_yolo.utils import echo_json, format_output, register_command


def register():
    register_command("eval", "评估：验证集评估、汇总、逐类分析", [
        {"name": "val", "args": ["--data", "--best-pt", "--batch"]},
        {"name": "summary", "args": ["--results-dir"]},
        {"name": "per-class", "args": ["--results-dir", "--class"]},
    ])


@click.group("eval")
def eval_cmd():
    """模型评估"""
    pass


@eval_cmd.command()
@click.option("--data", "data_yaml", required=True, type=click.Path(exists=True))
@click.option("--best-pt", required=True, type=click.Path(exists=True))
@click.option("--batch", type=int, default=16)
@click.option("--device", default=None)
@click.pass_context
def val(ctx, data_yaml, best_pt, batch, device):
    """在验证集上评估模型。"""
    from ultralytics import YOLO
    import tempfile, os

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        model = YOLO(best_pt)
        tmp_dir = tempfile.mkdtemp()
        metrics = model.val(data=data_yaml, batch=batch, device=device or "cpu",
                            plots=False, save_txt=False, save_json=False,
                            project=tmp_dir, name="val")
        shutil.rmtree(tmp_dir, ignore_errors=True)

        mean_vals = metrics.mean_results()
        summary = {
            "mAP50": round(mean_vals[2], 4) if len(mean_vals) > 2 else None,
            "mAP50-95": round(mean_vals[3], 4) if len(mean_vals) > 3 else None,
            "precision": round(mean_vals[0], 4) if len(mean_vals) > 0 else None,
            "recall": round(mean_vals[1], 4) if len(mean_vals) > 1 else None,
        }

        per_class = []
        names = metrics.names or {}
        for class_id, class_name in names.items():
            try:
                vals = metrics.class_result(class_id)
                per_class.append({
                    "class_id": class_id, "class_name": class_name,
                    "mAP50": round(vals[2], 4) if len(vals) > 2 else None,
                    "mAP50-95": round(vals[3], 4) if len(vals) > 3 else None,
                })
            except Exception:
                pass

        format_output({"summary": summary, "per_class": per_class}, fmt)
    except Exception as e:
        echo_json(None, ok=False, errors=[str(e)])


@eval_cmd.command()
@click.option("--results-dir", required=True, type=click.Path(exists=True))
@click.pass_context
def summary(ctx, results_dir):
    """读取 result_summary_log.csv 展示所有实验的评估汇总。"""
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    log_path = os.path.join(results_dir, "..", "logs", "result_summary_log.csv")
    # Also try results_dir directly
    alt_path = os.path.join(results_dir, "result_summary_log.csv")

    for path in [log_path, alt_path]:
        if os.path.exists(path):
            rows = []
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    rows.append(row)
            format_output({"source": path, "experiments": rows}, fmt)
            return

    echo_json(None, ok=False, errors=[f"未找到 result_summary_log.csv"])


@eval_cmd.command()
@click.option("--results-dir", required=True, type=click.Path(exists=True))
@click.option("--class", "class_name", default=None)
@click.pass_context
def per_class(ctx, results_dir, class_name):
    """逐类别评估指标。"""
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    log_path = os.path.join(results_dir, "..", "logs", "result_per_class_log.csv")
    alt_path = os.path.join(results_dir, "result_per_class_log.csv")

    for path in [log_path, alt_path]:
        if os.path.exists(path):
            rows = []
            with open(path, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    if class_name and row.get("class_name") != class_name:
                        continue
                    rows.append(row)
            format_output({"source": path, "per_class": rows}, fmt)
            return

    echo_json(None, ok=False, errors=[f"未找到 result_per_class_log.csv"])
```

- [ ] **Step 2: Commit**


### Task B5: log 命令 + log suggest

**Files:**
- Create: `isat_yolo/commands/log.py`

- [ ] **Step 1: 创建 `isat_yolo/commands/log.py`**

```python
"""Training log analysis commands."""
import os
import csv
import click
from isat_yolo.utils import echo_json, format_output, register_command


def register():
    register_command("log", "日志分析：历史、对比、调参建议", [
        {"name": "history", "args": ["--log-dir"]},
        {"name": "compare", "args": ["--log-dir", "--exp1", "--exp2"]},
        {"name": "suggest", "args": ["--log-dir", "--exp"]},
    ])


@click.group()
def log():
    """日志分析 & 调参建议"""
    pass


def _read_csv(csv_path):
    if not os.path.exists(csv_path):
        return []
    rows = []
    with open(csv_path, "r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


@log.command()
@click.option("--log-dir", required=True, type=click.Path(exists=True))
@click.pass_context
def history(ctx, log_dir):
    """列出训练历史记录。"""
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    train_log = _read_csv(os.path.join(log_dir, "train_log.csv"))
    summary_log = _read_csv(os.path.join(log_dir, "result_summary_log.csv"))
    format_output({"train_log": train_log, "result_summaries": summary_log}, fmt)


@log.command()
@click.option("--log-dir", required=True, type=click.Path(exists=True))
@click.option("--exp1", required=True)
@click.option("--exp2", required=True)
@click.pass_context
def compare(ctx, log_dir, exp1, exp2):
    """对比两个实验的指标。"""
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    rows = _read_csv(os.path.join(log_dir, "result_summary_log.csv"))
    r1 = next((r for r in rows if r.get("experiment_name") == exp1), None)
    r2 = next((r for r in rows if r.get("experiment_name") == exp2), None)
    if not r1 or not r2:
        echo_json(None, ok=False, errors=["未找到指定实验的记录"])
        return

    diffs = {}
    for key in ["box_map50", "box_map50_95", "mask_map50", "mask_map50_95"]:
        v1 = float(r1.get(key, 0) or 0)
        v2 = float(r2.get(key, 0) or 0)
        diffs[key] = {"exp1": v1, "exp2": v2, "diff": round(v2 - v1, 4)}

    winner = exp2 if sum(d["diff"] for d in diffs.values()) > 0 else exp1
    format_output({"exp1": r1, "exp2": r2, "diffs": diffs, "winner": winner}, fmt)


@log.command()
@click.option("--log-dir", required=True, type=click.Path(exists=True))
@click.option("--exp", "exp_name", default=None, help="指定实验名，默认分析最新实验")
@click.pass_context
def suggest(ctx, log_dir, exp_name):
    """分析训练结果，给出调参建议。"""
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    summary_rows = _read_csv(os.path.join(log_dir, "result_summary_log.csv"))

    if not summary_rows:
        echo_json(None, ok=False, errors=["未找到 result_summary_log.csv"])
        return

    if exp_name:
        target = next((r for r in summary_rows if r.get("experiment_name") == exp_name), None)
        if not target:
            echo_json(None, ok=False, errors=[f"未找到实验: {exp_name}"])
            return
    else:
        target = summary_rows[-1]  # latest

    # Analyze metrics
    suggestions = []
    analysis = {}

    mAP50 = float(target.get("box_map50", 0) or 0)
    mAP50_95 = float(target.get("box_map50_95", 0) or 0)

    analysis["mAP50"] = mAP50
    analysis["mAP50_95"] = mAP50_95

    # Underfitting check: low mAP on both train and val
    if mAP50 < 0.3:
        analysis["underfitting"] = {
            "detected": True,
            "detail": f"mAP50={mAP50}较低，模型可能欠拟合",
        }
        suggestions.append("模型欠拟合，建议增加epochs或使用更强的数据增强")

    # Check for class imbalance issues from per-class log
    per_class_rows = _read_csv(os.path.join(log_dir, "result_per_class_log.csv"))
    if per_class_rows:
        class_issues = []
        for row in per_class_rows:
            instances = int(row.get("instances", 0) or 0)
            cls_map50 = float(row.get("box_map50", 0) or 0)
            cls_name = row.get("class_name", "unknown")
            if instances < 20 and cls_map50 < 0.5:
                class_issues.append({
                    "class": cls_name, "instances": instances, "mAP50": cls_map50,
                    "status": "few", "suggestion": "数据量少且性能低，建议收集更多数据或启用更强增强"
                })
            elif instances > 500 and cls_map50 > 0.9:
                class_issues.append({
                    "class": cls_name, "instances": instances, "mAP50": cls_map50,
                    "status": "saturated",
                    "suggestion": "已接近性能上限"
                })
        analysis["class_balance"] = class_issues

        for ci in class_issues:
            if ci["status"] == "few":
                suggestions.append(ci["suggestion"])

    # Generic suggestions based on common patterns
    if mAP50_95 < mAP50 * 0.5:
        suggestions.append("mAP50-95远低于mAP50，模型定位精度有提升空间，尝试减小imgsz或增大batch")

    if not suggestions:
        suggestions.append("模型表现正常，可以尝试微调获得更好结果")

    format_output({
        "experiment": target.get("experiment_name", "unknown"),
        "metrics": {"mAP50": mAP50, "mAP50_95": mAP50_95},
        "analysis": analysis,
        "suggestions": suggestions,
    }, fmt)
```

- [ ] **Step 2: Commit**


### Task B6: predict 命令

**Files:**
- Create: `isat_yolo/commands/predict.py`

- [ ] **Step 1: 创建 `isat_yolo/commands/predict.py`**

```python
"""Prediction/inference commands."""
import os
import click
from isat_yolo.utils import echo_json, format_output, register_command


def register():
    register_command("predict", "推理：单图、批量、视频", [
        {"name": "image", "args": ["--model", "--source", "--conf", "--save-dir"]},
        {"name": "batch", "args": ["--model", "--source", "--conf"]},
        {"name": "video", "args": ["--model", "--source", "--conf"]},
    ])


@click.group()
def predict():
    """模型推理"""
    pass


@predict.command()
@click.option("--model", "model_path", required=True, type=click.Path(exists=True))
@click.option("--source", required=True, type=click.Path(exists=True))
@click.option("--conf", type=float, default=0.25)
@click.option("--save-dir", default=None, type=click.Path())
@click.pass_context
def image(ctx, model_path, source, conf, save_dir):
    """单张图片推理。"""
    from ultralytics import YOLO
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        model = YOLO(model_path)
        results = model.predict(source=source, conf=conf, save=bool(save_dir),
                                project=save_dir or "runs/predict", exist_ok=True)
        detections = []
        for r in results:
            boxes = r.boxes
            if boxes is not None:
                for i in range(len(boxes)):
                    cls_id = int(boxes.cls[i].item())
                    detections.append({
                        "class": model.names.get(cls_id, str(cls_id)),
                        "confidence": round(boxes.conf[i].item(), 4),
                        "bbox": [round(x, 1) for x in boxes.xyxy[i].tolist()],
                    })
        format_output({"source": source, "num_detections": len(detections),
                       "detections": detections}, fmt)
    except Exception as e:
        echo_json(None, ok=False, errors=[str(e)])


@predict.command()
@click.option("--model", "model_path", required=True, type=click.Path(exists=True))
@click.option("--source", required=True, type=click.Path(exists=True))
@click.option("--conf", type=float, default=0.25)
@click.pass_context
def batch(ctx, model_path, source, conf):
    """批量推理（图片目录）。"""
    from ultralytics import YOLO
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        model = YOLO(model_path)
        results = model.predict(source=source, conf=conf, save=True,
                                project="runs/predict", exist_ok=True)
        total = sum(1 for r in results if r.boxes is not None for _ in r.boxes)
        format_output({"source": source, "images_processed": len(results),
                       "total_detections": total}, fmt)
    except Exception as e:
        echo_json(None, ok=False, errors=[str(e)])


@predict.command()
@click.option("--model", "model_path", required=True, type=click.Path(exists=True))
@click.option("--source", required=True, type=click.Path(exists=True))
@click.option("--conf", type=float, default=0.25)
@click.pass_context
def video(ctx, model_path, source, conf):
    """视频推理。"""
    from ultralytics import YOLO
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    try:
        model = YOLO(model_path)
        results = model.predict(source=source, conf=conf, save=True,
                                project="runs/predict", exist_ok=True)
        format_output({"source": source, "frames_processed": len(results)}, fmt)
    except Exception as e:
        echo_json(None, ok=False, errors=[str(e)])
```

- [ ] **Step 2: Commit**


### Task B7: config 命令

**Files:**
- Create: `isat_yolo/commands/config_cmd.py`

- [ ] **Step 1: 创建 `isat_yolo/commands/config_cmd.py`**

```python
"""Configuration management commands."""
import click
from dataclasses import asdict
from isat_yolo.config import TrainConfig, load_effective_config, save_user_config, merge_config
from isat_yolo.utils import echo_json, format_output, register_command


def register():
    register_command("config", "配置管理：查看、设置默认训练参数", [
        {"name": "show", "args": []},
        {"name": "set", "args": ["--epochs", "--imgsz", "--batch", "--device", "..."]},
    ])


@click.group()
def config():
    """配置管理"""
    pass


@config.command()
@click.pass_context
def show(ctx):
    """显示当前生效的完整配置。"""
    cfg = load_effective_config()
    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output(asdict(cfg), fmt)


@config.command()
@click.option("--epochs", type=int, default=None)
@click.option("--imgsz", type=int, default=None)
@click.option("--batch", type=int, default=None)
@click.option("--device", type=str, default=None)
@click.option("--lr0", type=float, default=None)
@click.option("--close-mosaic", type=int, default=None)
@click.option("--multi-scale", type=float, default=None)
@click.option("--augment/--no-augment", "use_augment", default=None)
@click.pass_context
def set(ctx, **kwargs):
    """保存训练参数为默认配置（写入 ~/.yolo-lab/config.yaml）。"""
    overrides = {k: v for k, v in kwargs.items() if v is not None}
    if not overrides:
        echo_json(None, ok=False, errors=["至少指定一个要设置的参数"])
        return

    current = load_effective_config()
    updated = merge_config(current, overrides)
    save_user_config(updated)

    fmt = ctx.obj.get("fmt", "json") if ctx.obj else "json"
    format_output({"saved": overrides, "config_file": "~/.yolo-lab/config.yaml"}, fmt)
```

- [ ] **Step 2: Commit**


### Task B8: isat_yolo logger

**Files:**
- Create: `isat_yolo/logger.py`

- [ ] **Step 1: 创建 `isat_yolo/logger.py`**

```python
"""Training log CSV management."""
import os
import csv
from datetime import datetime


def get_timestamp() -> str:
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ensure_log_dir(log_dir: str):
    os.makedirs(log_dir, exist_ok=True)


# ── train_log.csv ──

def _ensure_train_csv_header(csv_path: str):
    if not os.path.exists(csv_path):
        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time", "mode", "status", "experiment_name", "model_file",
                "data_yaml", "epochs", "imgsz", "batch", "device",
                "save_dir", "best_pt", "last_pt", "notes",
            ])


def append_train_log(config, mode: str, status: str, notes: str = ""):
    ensure_log_dir(config.log_dir)
    csv_path = os.path.join(config.log_dir, "train_log.csv")
    _ensure_train_csv_header(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            get_timestamp(), mode, status, config.experiment_name,
            config.model_file, config.data_yaml, config.epochs,
            config.imgsz, config.batch, config.device,
            config.save_dir, config.best_pt, config.last_pt, notes,
        ])


# ── result_summary_log.csv ──

def _ensure_result_summary_csv_header(csv_path: str):
    if not os.path.exists(csv_path):
        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time", "mode", "experiment_name", "best_pt",
                "images", "instances",
                "box_p", "box_r", "box_map50", "box_map50_95",
                "mask_p", "mask_r", "mask_map50", "mask_map50_95",
                "notes",
            ])


def append_result_summary_log(config, mode: str, summary: dict, notes: str = ""):
    ensure_log_dir(config.log_dir)
    csv_path = os.path.join(config.log_dir, "result_summary_log.csv")
    _ensure_result_summary_csv_header(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            get_timestamp(), mode, config.experiment_name, config.best_pt,
            summary.get("images", ""), summary.get("instances", ""),
            summary.get("box_p", ""), summary.get("box_r", ""),
            summary.get("box_map50", ""), summary.get("box_map50_95", ""),
            summary.get("mask_p", ""), summary.get("mask_r", ""),
            summary.get("mask_map50", ""), summary.get("mask_map50_95", ""),
            notes,
        ])


# ── result_per_class_log.csv ──

def _ensure_result_per_class_csv_header(csv_path: str):
    if not os.path.exists(csv_path):
        with open(csv_path, mode="w", newline="", encoding="utf-8-sig") as f:
            writer = csv.writer(f)
            writer.writerow([
                "time", "mode", "experiment_name", "best_pt",
                "class_id", "class_name", "images", "instances",
                "box_p", "box_r", "box_map50", "box_map50_95",
                "mask_p", "mask_r", "mask_map50", "mask_map50_95",
                "notes",
            ])


def append_result_per_class_log(config, mode: str, class_rows: list, notes: str = ""):
    ensure_log_dir(config.log_dir)
    csv_path = os.path.join(config.log_dir, "result_per_class_log.csv")
    _ensure_result_per_class_csv_header(csv_path)
    with open(csv_path, mode="a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        for row in class_rows:
            writer.writerow([
                get_timestamp(), mode, config.experiment_name, config.best_pt,
                row.get("class_id", ""), row.get("class_name", ""),
                row.get("images", ""), row.get("instances", ""),
                row.get("box_p", ""), row.get("box_r", ""),
                row.get("box_map50", ""), row.get("box_map50_95", ""),
                row.get("mask_p", ""), row.get("mask_r", ""),
                row.get("mask_map50", ""), row.get("mask_map50_95", ""),
                notes,
            ])


# ── Metric extraction ──

def extract_seg_val_metrics(metrics, class_image_counts=None, class_instance_counts=None):
    """Extract summary and per-class metrics from Ultralytics model.val() result."""
    class_image_counts = class_image_counts or {}
    class_instance_counts = class_instance_counts or {}

    mean_vals = metrics.mean_results()
    summary = {
        "images": sum(class_image_counts.values()) if class_image_counts else "",
        "instances": sum(class_instance_counts.values()) if class_instance_counts else "",
        "box_p": mean_vals[0] if len(mean_vals) > 0 else "",
        "box_r": mean_vals[1] if len(mean_vals) > 1 else "",
        "box_map50": mean_vals[2] if len(mean_vals) > 2 else "",
        "box_map50_95": mean_vals[3] if len(mean_vals) > 3 else "",
        "mask_p": mean_vals[4] if len(mean_vals) > 4 else "",
        "mask_r": mean_vals[5] if len(mean_vals) > 5 else "",
        "mask_map50": mean_vals[6] if len(mean_vals) > 6 else "",
        "mask_map50_95": mean_vals[7] if len(mean_vals) > 7 else "",
    }

    per_class_rows = []
    names = metrics.names or {}

    def _is_valid_class(cname):
        if cname is None:
            return False
        s = str(cname).strip().lower()
        return s not in {"none", "", "background", "__background__"}

    valid_classes = [(cid, cname) for cid, cname in names.items() if _is_valid_class(cname)]

    for idx, (class_id, class_name) in enumerate(valid_classes):
        try:
            vals = metrics.class_result(idx)
        except Exception:
            vals = []
        row = {
            "class_id": class_id, "class_name": class_name,
            "images": class_image_counts.get(class_name, 0),
            "instances": class_instance_counts.get(class_name, 0),
            "box_p": vals[0] if len(vals) > 0 else "",
            "box_r": vals[1] if len(vals) > 1 else "",
            "box_map50": vals[2] if len(vals) > 2 else "",
            "box_map50_95": vals[3] if len(vals) > 3 else "",
            "mask_p": vals[4] if len(vals) > 4 else "",
            "mask_r": vals[5] if len(vals) > 5 else "",
            "mask_map50": vals[6] if len(vals) > 6 else "",
            "mask_map50_95": vals[7] if len(vals) > 7 else "",
        }
        per_class_rows.append(row)

    return summary, per_class_rows
```

- [ ] **Step 2: Commit**

---

## Part C: Integration

### Task C1: setup.py entry_points

**Files:**
- Modify: `setup.py` (只追加，不改原配置)

- [ ] **Step 1: 修改 setup.py**

```python
# 在 setup.py 的 entry_points 中追加:
entry_points={
    "console_scripts": [
        "isat-sam=ISAT.main:main",              # 原有，不动
        "isat-agent=isat_agent_cli.cli:main",   # 新增
        "isat-yolo=isat_yolo.cli:main",         # 新增
    ],
    "isat.plugins": [],                          # 原有，不动
},
```

- [ ] **Step 2: pip install 验证**

```bash
cd /home/ljz/vibe_coding/YOLO/isat-yolo-lab
pip install -e .
which isat-agent
which isat-yolo
isat-agent --help
isat-yolo --help
isat-agent capabilities
isat-yolo capabilities
```

- [ ] **Step 3: Commit**

---

### Task C2: 端到端验证

- [ ] **Step 1: 完整流程测试**

```bash
# 1. Agent CLI: 创建项目
isat-agent project init --images /tmp/e2e-test/images --categories 猫,狗,鸟 --output /tmp/e2e-test/project

# 2. Agent CLI: capability发现
isat-agent capabilities | python -c "import sys,json; d=json.load(sys.stdin); print(f'{len(d[\"commands\"])} command groups')"

# 3. ISAT GUI 打开项目手动标注（模拟）
# (手动创建1-2个json标注文件用于测试)

# 4. Agent CLI: 转换格式
isat-agent convert isat2yolo --json-root /tmp/e2e-test/project --txt-root /tmp/e2e-test/yolo-labels

# 5. YOLO CLI: 准备数据集
isat-yolo dataset init --json-root /tmp/e2e-test/project --images /tmp/e2e-test/images --out /tmp/e2e-test/dataset

# 6. YOLO CLI: 拆分 + 生成yaml
isat-yolo dataset split --dataset /tmp/e2e-test/dataset
isat-yolo dataset yaml --dataset /tmp/e2e-test/dataset --names 猫,狗,鸟

# 7. YOLO CLI: 查看配置
isat-yolo config show

# 验证: 所有命令都返回 {"ok": true, ...} 结构
```

- [ ] **Step 2: Commit**

---

## Implementation Order

建议实现顺序：
1. **A1** (骨架) → **C1** (setup.py) → 立即可测
2. **A4** (convert) → 最快产出价值
3. **A2** (project) **A3** (category) **A5** (stats)
4. **A6** (validate) **A7** (batch) **A8** (media) **A9** (model)
5. **A10** (集成测试)
6. **B1** (骨架+config) **B8** (logger)
7. **B2** (dataset) **B7** (config)
8. **B3** (train) **B4** (eval)
9. **B5** (log/suggest) **B6** (predict)
10. **C2** (端到端)
