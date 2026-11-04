# 不完整结构及外部项目打开 Implementation Plan

> 用户尚无完整结构，按已明确的“内容符合即可打开”要求定义最低标准，单代理在当前分支原地执行，保留所有已有改动，不提交或推送。

**Goal:** 图片文件夹即可打开，不再要求本软件生成的标记或完整目录；兼容 ISAT 图片/JSON 与有效 YOLO 数据配置，保持原目录不变和删除保护。

**Architecture:** 新增只读内容识别模块。外部来源的状态和筛选副本保存在配置目录下按源路径及目录身份隔离的工作区。最近项目和 current_root 始终指向来源路径，工作台的配置、筛选和输出使用独立 storage_root。原生新建项目沿用现有存储及所有权证明。

## 标准与边界

- 至少一张可读取图片即可打开，JSON 和 labels 目录不是必需项；空目录、仅有文件夹名、损坏标注/配置给出明确错误。
- ISAT 支持图片旁 JSON，以及 images/json 对应结构；JSON 需与对应图片尺寸和 ISAT 格式匹配。
- YOLO 配置读取 names、train 及存在的 val/test，校验路径、图片及现有标签；缺失标签允许作为未标注图。有效配置自动填入模型开发，不启动训练，也不假装将 YOLO 标签转换成 ISAT。
- 源路径、工作记录和删除资格分开。外部来源不写 marker、projects、配置或输出；整目录删除始终禁止，列表移除保留源文件。
- 切换守卫通过后才创建独立工作记录。当前来源删除后不重建；不同来源及原生项目相互隔离。
- 首次筛选异步复制源图和有效 ISAT 标签，之后恢复已保存的副本，不重复导入覆盖修改。

### Task 1: 内容识别和独立状态

Files: `ISAT/workspaces/external.py`, `ISAT/workspaces/store.py`, `ISAT/data_screening/session.py`, `tests/workspaces/test_external.py`。

- [x] RED：无标记图片目录、ISAT 对应 JSON、YOLO 配置；错误尺寸/路径/标签/链接拒绝且无写入。
- [x] GREEN：只读识别，外部元数据及封面放入独立存储，最近记录保留源路径，禁止外部整目录删除；原生行为回归不变。

### Task 2: 工作台接入

Files: `ISAT/workspaces/integration.py`, `tests/workspaces/test_integration.py`, `tests/workspaces/test_home.py`。

- [x] RED：图片打开后出现筛选副本，ISAT 标签保留，YOLO 配置进入模型开发；状态跨切换保留，后台任务拦截不提前写入。
- [x] GREEN：current_root 与 storage_root 分离，首次导入和后续恢复，源删除/移除/退出不重建原目录；补充同路径替换、切换期间替换、内部路径显示的 RED/GREEN。

### Task 3: 验证及文档

- [x] 全量测试、真实选择框和图片/ISAT/YOLO 工作台验证；检查源文件快照、配置 hash、diff，并更新最低标准说明。
