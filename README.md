# 鸣潮角色 Mod 制作与排错 Skill

供 Codex 在 Windows 上使用的 XXMI / WWMI 角色外观 Mod 制作与修复技能。基于本地采集和实际着色器证据进行材质适配、权重转移及游戏验证。

适用于服装替换、阶段换装/溶解、原皮纹理残留、拉伸尖角、黑影和近镜头透视。已有兼容三维资源时可自动化适配；只有参考图片时先判断资源可行性，不承诺自动补齐模型、UV和动画权重。

## 安装与调用

将 `skills/wwmi-character-mod` 整个目录复制到 `%USERPROFILE%\.codex\skills\wwmi-character-mod`；已有同名技能时先备份并合并所需更新。也可使用 Codex 的 skill-installer，指定本仓库及路径 `skills/wwmi-character-mod`。

在 Codex 中调用：

> 使用 $wwmi-character-mod，检查当前 XXMI/WWMI 环境，并按本地证据制作或修复鸣潮角色外观 Mod。

## 内容

- [技能入口](skills/wwmi-character-mod/SKILL.md)：工作范围、流程及参考路由。
- [阶段效果](skills/wwmi-character-mod/references/stage-effects.md)：逐层证据、停画/溶解区分、定向规则与验证边界。
- [运行时排错](skills/wwmi-character-mod/references/runtime-debugging.md)：材质槽、F8采集、ShaderRegex、截图与配置恢复。
- [网格与权重](skills/wwmi-character-mod/references/geometry-and-build.md)：缓冲区接口、供体选择、骨骼重映射与三角形检查。
- [长离案例](skills/wwmi-character-mod/references/changli-case.md)、[守岸人案例](skills/wwmi-character-mod/references/shorekeeper-case.md)：已验证经验及仍未解决的边界。
- `scripts/inspect_wwmi.py`：只读解析实际导入器路径、快捷键、采集开关与导出范围。
- `scripts/audit_shader.py`：只读列出淡出组合、discard与临时参数线索。
- `scripts/capture_game.ps1`：按物理像素截取本地游戏窗口，需要随后人工或模型查看。

只读 Python 工具使用 Python 3 标准库；截图脚本使用 Windows PowerShell/.NET。实际制作需用户本机的 XXMI/WWMI、适用素材及相应构建工具。

## 证据与限制

案例中的哈希、参数槽、阈值及坐标只适用于当时采集，不能直接套到其他角色或客户端。F10刷新不等于F8帧分析；正则命中也不等于画面验证。局部外观修复不代表官方全部阶段、燃烧边缘与大招时序已精确复刻。

本仓库只包含技能说明和辅助脚本，不包含游戏模型、贴图、采集、截图、账号信息或可直接安装的角色Mod。`<PROJECT_ROOT>`、`<WWMI_ROOT>`、`<GAME_ROOT>`为本机路径占位符。游戏素材权利与工具/技能许可分别对待。

## 许可与来源

本仓库原创技能说明及辅助脚本采用 [MIT](LICENSE)。鸣潮及相关角色/素材归其权利人所有，不受本仓库许可覆盖。方法参考 [WWMI-Tools](https://github.com/SpectrumQT/WWMI-Tools)、[WWMI-Assets](https://github.com/SpectrumQT/WWMI-Assets) 和 [3DMigoto](https://github.com/bo3b/3Dmigoto)，并以当前本地实现及实测证据为准。
