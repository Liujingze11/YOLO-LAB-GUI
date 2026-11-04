# SDD ledger — plan: docs/superpowers/plans/2026-10-30-data-screening.md

Spec: docs/superpowers/specs/2026-10-30-data-screening.md

Ruling: 原图编辑方式尚未收到答复，按已说明的副本方案实施 — 不损失原图，可满足筛选后导入 — 如果用户要求直接修改原文件再调整。
Ruling: 当前 feature 分支原地实现并自审，不分派代理 — 用户与 CLAUDE.md 要求单代理，保留现有改动 — 无独立代理审查。
Pre-flight: Task 1 的项目结果字典由 Task 2 signal 传到 Task 3；统一 project_root/image_root/label_root/files，未发现冲突。
Pre-flight: Task 2 的 active_workers/stop_workers 交由 Task 3 关闭守卫；统一 stop() 可取消，未发现冲突。

Task 1: complete — 8 个初始测试均由缺少模块 RED 到 GREEN。另补一项源文件在已复制后改变的复现（RED），最终发布前重新校验所有源文件（GREEN）。
Task 2: complete — 5 个初始 Qt 页面测试 RED→GREEN；后台线程结束后释放 QObject；补充取消后 queued loaded 结果复现（RED），通过取消状态屏蔽迟到回调（GREEN）。
Task 3: complete — 3 个初始导航/导入测试 RED→GREEN，额外真实 QThread 忙状态测试。修正循环变量遮蔽导航 action 的问题。全套 42 项通过，11.008 秒。
Ruling: 未保存标注仅在实际切换画布之前询问一次 — 导入生成文件后若用户取消切换，保留旧画布和已生成项目，允许再次点击打开 — 不重复复制且不丢弃标注。
Ruling: 检测到原 software.yaml 从 en 改为 zh；将当前字节仅在内存里恢复 en 后的 SHA256 恰为原 1ce3a431… — 用户运行中配置更新需要保留，未回滚 — 新基线 a538c2368fe057a70b13bb61b709bf0cd94ce31f6a0b3dca39a9179ee7ba7fa0。
Verification: 实际原生页面和导入后的标注画布截图已保存；真实保存的 JSON 在 json/，images/ 无 JSON；验证前后当前 software.yaml 字节一致。
Self-review: 单代理要求优先于审查技能的分派条款；已审查新模块及集成改动，没有未处理的阻断问题。现有启动器和图标改动一并保留，未提交软件配置、未推送远程。
