# 项目卡片管理 Implementation Plan

> 使用 superpowers:executing-plans，按既有要求单代理在当前 feature 分支原地执行，保留已有修改，不提交或推送。

**Goal:** 恢复项目命名，添加右键项目操作，并隐藏已被外部删除的项目。

**Architecture:** 延用 WorkspaceStore、WorkspaceHome、WorkspaceHomeController。新建先选父目录，再命名并创建同名子目录，成功后进入工作台。菜单提供打开、打开文件夹、复制路径、删除；删除明确确认后移入系统回收站。当前项目删除前处理未保存内容和任务，删除后解除工作台引用，避免退出时重建旧路径。

**Tech Stack:** Python 3.10、PyQt5 5.15（QFile.moveToTrash）、unittest。

## Global Constraints

- 当前用户请求替代之前“选目录直接进入”的简化：恢复命名步骤，创建成功后仍自动进入。
- 项目名称与文件夹名称一致，同名不覆盖，取消不写文件。
- 目录或项目标记已不存在时，首页不显示失效卡片；兼容旧版未迁移空间。
- 删除移入系统回收站，不永久清除数据；取消、后台任务或文件操作失败时保留原项目。

## Review Focus

- 外部删除目录或标记后，刷新/重启/退出不能重建该项目。
- 删除当前项目须清空路径引用，保留未保存内容和任务守卫。
- 旧版工作空间需继续显示，显式删除后不能从旧的选择记录重新冒出。
- 新建命名与目录一致，取消及同名冲突不覆盖文件。
- 回收站不可用时保持卡片和文件，显示操作失败。

### Task 1: 记录有效性与移除

Files: `ISAT/workspaces/store.py`, `tests/workspaces/test_store.py`。

- [x] RED：缺失目录/标记不展示，旧位置兼容，forget 清除索引与旧选择记录但不删文件。
- [x] GREEN：过滤无效卡片，显式保留旧版标志，阻止状态更新重造已删项目标记。

### Task 2: 命名与右键菜单

Files: `ISAT/workspaces/home.py`, `tests/workspaces/test_home.py`。

- [x] RED：先选位置再命名，名称作为子目录，取消命名无写入，菜单打开/复制/删除信号正确。
- [x] GREEN：恢复简洁命名窗口；卡片右键菜单，保持首页短提示。

### Task 3: 删除守卫及验证

Files: `ISAT/workspaces/integration.py`, `tests/workspaces/test_integration.py`。

- [x] RED：确认/取消删除、当前项目解除、任务守卫、外部删除后退出不重建。
- [x] GREEN：确认后移入回收站，清理当前状态及索引，失败保留项目。
- [x] 完整 unittest 回归、实际菜单/命名/删除界面检查、配置 hash 与 diff 检查。
