# 守岸人底部透视、衣料淡出和鞋底发黑：2026-10-15案例

本机复盘与检索入口，不是跨角色/跨版本补丁。用户最终明确回复“鞋底问题也已解决”“全部正常”。完成状态依据局部截图、实际着色器导出和用户确认；没有补写完整动作、切人或其他角色回归验证。

## 工程与回退

- 工作目录 `<PROJECT_ROOT>`；实际 WWMI `<WWMI_ROOT>`，来自XXMI启动器配置。
- 安装文件 `<WWMI_ROOT>/Mods/守岸人-鸣乐之时2.0 by nom（0切换）/NoM_ShoreKeeper_ResonatesV3.2(Min)/mod.ini`。
- 完整修正版 `output/Shorekeeper_LocalFadeFix/mod.ini.staged`，相对最初版本差异 `fade-fix.patch`。
- 原始/中间版本备份与哈希、作用域、证据在 `reports/shorekeeper_fade_patch.json`，快照副本位于 `reports/shorekeeper-fade-backup/`。
- `python -X utf8 scripts/install_shorekeeper_fade_fix.py check` 核对当前哈希；`restore` 仅在安装内容未发生其他改动时回退至最初备份，然后手动F10。运行前先检查脚本及实时状态，不能用案例哈希覆盖新版本。
- 最终安装SHA256 `821f7bc810d5f05b57519f14752ac7e85fb88bc4b867e0a7c95a36a07b6b459d`。保留原有网格和切换draw列表；未修改RabbitFX提供者。

## 材质与部件定位

实际轻量采集 `<WWMI_ROOT>/FrameAnalysis-2026-10-14-235136/log.txt`：

| 原始调用 | VS | PS | 实际用途/证据 |
|---|---|---|---|
| 174，身体原始102810/77982 | 02f5c4b333a78fa0 | 36adaa46af9a078c | MRT：normal t0、lightmap t1、diffuse t2 |
| 187，同部件 | e4a3da6d1d1068b9 | 36b2debf378ddd75 | 前向从t0读颜色，API却将diffuse放t2 |
| 202，同部件 | 1ea1774712644e9b | 1a9f93d57a9289f7 | 第三通道，输出零颜色仍有discard；未仅凭此断言是阴影或深度 |

前向原始t0描述符被RabbitFX分类为1718.7，MRT法线t0为1718.3。在身体部件绘制组内，仅当 `ps==1718.1 && ps-t0==1718.7` 时将t0指向ResourceBase，前后保存恢复原槽。这个分类来自实际安装的RabbitFX 6.18，不能当通用材质类型常数。

源坐标/UV和draw索引区分了部件：

- 主身体四套draw为 `114327/131388`、`126786/249099`、`114327/375885`、`126786/490212`，由TBS选择。
- 脸是独立部件2，draw `13392/105786`；前后头发是部件0/1。
- 鞋是部件4中的 `24180/1828947`，高度约0.82–19.61；部件3与部件4F均不是鞋。
- 按存储法线筛选的212个朝下鞋底三角形，UV采样源颜色中位数约RGB207，非纯黑；整个鞋含大量暗色，不能用全鞋颜色替代鞋底结论。
- 原始三角形叉积在身体和鞋上均与存储法线反向，是统一约定线索；没有据此翻转法线。

详见 `reports/shorekeeper_material_pass_evidence.json`、`shorekeeper_draw_bounds.json`、`shorekeeper_shoe_source_colors.json`、`shorekeeper_shoe_normals.json`。鞋底最后由用户确认恢复，没有单独隔离导致它发黑的唯一因子。

## 两层淡出与作用域

第一版仅在四个不透明主身体draw前后保存/设置/恢复x240，绕过 `min → add(-0.333000) → lt(0) → discard_nz` 的最终丢弃。与当时长离规则有意共享同义契约，并带本地fallback。身体恢复，但脸、头发和衣料仍有问题。这不是适合所有有透明裁切部件的方案。

第二版用x243覆盖一个由 `movc → add → mad` 计算的中间因子，只在部件4范围内置1。实际导出证明编译，但更低角度仍虚化：MRT中另一项r0.x仍参与min；前向中另一项r1.z仍参与min。中间因子命中不等于最终discard失效，且脸根本不在作用域内。初步命名为相机因子缺乏完整依据，后续应按数据来源和行为验证。

最终版本保留前两项已生效修正，并补充：

- x243作用域覆盖部件0、1、2、4，每组保存恢复；不嵌套同一保存变量。
- MRT/第三通道：识别屏幕位置/宽高比计算的遮罩末尾，将独立mask置1后再参与最终组合。
- 前向：在屏幕遮罩末尾 `add(mask,-1) → mad(mask,cb...,mask,1)` 与后续min之间置mask为1。
- 保留独立纹理alpha、其他discard及材质资源，不全局删除丢弃，不设置cull=none。

已采集正例中，各屏幕遮罩模式匹配一次：身体三个通道、脸的MRT/前向/第三通道、头发的对应通道。脸还有 `f3a3d977b852fa96` 变体，不匹配这两个屏幕模式，不能声称所有shader都匹配。临时参数和正则匹配位置需以后重新核验。当前完成不等于这些正则可直接复用于其他角色。

## 证据与经验边界

- `shorekeeper_face_cloth_remaining.png` 清楚记录修正前脸/胸前衣料点阵。
- `shorekeeper_after_screenmask.png` 记录修正后脸/头发/胸前衣服连续表面；光照和视角有变化，未做像素级可比断言。
- 用户继续下转镜头后确认“全部正常”，鞋底也明确确认解决。停止要求追加旧任务测试。
- Oracle咨询已返回 `reports/oracle-shore-censor-review.md`，确认中间因子可能被后续min限制，但未提供可直接采用的精确安全补丁；最终根据本地完整通道证据实施。浏览器复用当前模型，实际模型标签未验证。
- Hunting/export_fixed曾出现其他后续更改，收尾没有覆盖来源不明的新值。不要用旧配置备份覆盖他人的设置。

可迁移结论：按部件及通道追踪，从最终可见性判定往前拆分因子；截图、编译、作用域和用户确认是四种不同证据。保留反例和失败修正的边界，比保存一个“万能正则”更有用。
