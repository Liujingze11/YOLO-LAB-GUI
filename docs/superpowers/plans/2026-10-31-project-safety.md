# 项目目录保护与卡片一致性 Implementation Plan

> 使用 superpowers:executing-plans，遵循既有单代理原地开发要求，不提交、不推送，保留已有修改。用户已明确要求修复布局、移除误建桌面卡片、强制命名并检查误删风险。

**Goal:** 卡片尺寸一致；新建必须填写名称；旧版直接选中的目录不得被当作软件创建的项目整目录删除。

**Architecture:** 在 WorkspaceStore 中集中验证名称、保护位置及项目创建来源。仅 create 在排他新建的子目录写入创建来源，旧目录不自动升级。首页清理受保护位置的记录，仅修改配置；已有目录提供“从列表移除”。删除前后验证同一目录及创建标识，禁止确认窗口期间替换目标。

**Tech Stack:** Python、PyQt5、unittest；沿用系统回收站，不引入依赖。

## Global Constraints

- 不删除桌面文件，不移除桌面下正常命名的子项目。
- 命名框初始为空；空白、路径穿越、非法名称、同名文件夹不可创建。
- 桌面、主目录、常见用户目录、系统顶层目录及应用配置所在目录受保护。
- 只有有本次新建来源记录且路径匹配的项目才允许整目录删除；旧版目录只允许从列表移除。
- 项目卡片与新建卡片始终等宽等高，窗口缩放及刷新后不拉伸。

## Review Focus

- 旧版有 marker 的桌面，及仅有 projects 的旧选择位置。
- 从列表移除父目录不误移除子项目，不操作任何项目文件。
- 软链接指向项目/用户目录，或确认弹窗期间目录被替换。
- 名称为空、仅空格、非法字符、已有同名目录，回车不能绕过验证。
- 未保存内容及后台任务仍保留原有守卫。

### Task 1: 名称和布局

Files: `ISAT/workspaces/home.py`, `ISAT/workspaces/store.py`, `tests/workspaces/test_home.py`, `tests/workspaces/test_store.py`。

- [x] RED：命名初始为空且无法提交，非法名称无法提交；不同卡片数量及多次缩放后尺寸一致。
- [x] GREEN：共用名称校验，明确子目录预览，固定卡片大小并按可用宽度排列；补充旧卡片立即隐藏的 RED/GREEN，防止刷新后重复显示。

### Task 2: 目录保护和来源

Files: `ISAT/workspaces/store.py`, `tests/workspaces/test_store.py`。

- [x] RED：桌面记录隐藏，重开仍隐藏且文件不变；旧目录禁止删除；新建项目及软链接/来源篡改验证。
- [x] GREEN：关闭直接初始化已有目录的旧入口，加入保护位置过滤和仅由 create 写入的来源；清理不安全历史及旧选择记录。

### Task 3: 安全操作与验证

Files: `ISAT/workspaces/home.py`, `ISAT/workspaces/integration.py`, `tests/workspaces/test_integration.py`。

- [x] RED：旧目录直接调用删除也不能动文件；移除列表不删文件且不重现；确认期间替换目录后不得删除。
- [x] GREEN：右键提供从列表移除；删除入口和执行前均验证创建来源及目录身份。
- [x] 完整测试、真实原生弹窗/等宽卡片/回收站验证，配置 hash 与 diff 检查，更新用户文档及验证记录。
