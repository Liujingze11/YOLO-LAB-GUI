# 打开已有项目 Implementation Plan

> 使用 superpowers:executing-plans，遵循既有单代理本地开发方式，保留已有改动，不创建工作树、不提交、不推送。

**Goal:** 除新建外，首页可选择已有项目并恢复工作台，保持之前的目录删除保护。

**Architecture:** “新建项目”旁加入同尺寸的“打开项目”卡片，说明为“选择已有项目文件夹”。选择后只读检查有效项目记录，再走现有 workspace_requested / open_workspace 流程；任务和未保存内容守卫通过后才登记最近项目。普通目录不能初始化为项目，不补发创建来源，不放宽删除权限。

**Tech Stack:** 原生 PyQt5、Python、unittest。

## Constraints and Review Focus

- 两张入口卡片和项目卡片保持同尺寸，短文案，无新增右上角按钮。
- 明确选择创建时命名的项目文件夹；缺失或损坏项目记录、普通文件夹、桌面及链接拒绝打开，不写入目录。
- 取消不写文件；打开保留原名、参数、图片和文件，不创建嵌套项目或弹出命名。
- 成功打开加入最近列表且不重复；受任务或未保存内容阻止时不提前登记。
- 被复制/移动的项目可打开，但不因此获得整目录删除权限。

### Task 1: 入口及只读验证

Files: `ISAT/workspaces/home.py`, `ISAT/workspaces/store.py`, `tests/workspaces/test_home.py`, `tests/workspaces/test_store.py`。

- [x] RED：选择有效项目只发送打开请求；取消、普通/伪造/损坏目录不产生请求和写入。
- [x] GREEN：新增打开卡片和目录选择器；`WorkspaceStore.read_existing(root)` 只读检查项目 marker，旧 open_location 入口也不再接受仅有 projects 的普通目录。

### Task 2: 工作台与安全回归

Files: `tests/workspaces/test_integration.py`, documentation and verification script。

- [x] RED/GREEN：实际卡片进入工作台、恢复训练参数、重复打开去重；任务拦截不登记；复制目录打开不改变删除资格。
- [x] 全量回归、真实目录选择器/首页截图、配置 hash 与 diff 检查，记录结果。
