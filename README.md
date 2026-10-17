# DesignerBIM P01 — 门组件二维／三维联动原型

**v0.2.0 · Blender 5.2.2 · 测试候选版，不是生产 BIM 软件。**

从固定三樘门演示推进到可编辑门实例：新增／复制、沿墙精确定位、门高与左右开向，并同步真实墙洞、三维、平面、立面和尺寸。扩展 ID 与更新地址不变。

## 更新

```text
https://raw.githubusercontent.com/ArchitectureWorld/blender-designerBIM/main/extensions/index.json
```

已安装远程版：保存并另存 `.blend` 备份，在 **编辑 → 偏好设置 → 获取扩展 → 检查更新** 中更新 DesignerBIM，再重启 Blender。不要添加第二个存储库，也不要同时启用本地旧版与远程版。

第一次使用：添加上述远程存储库并安装；三维视图按 **N → DesignerBIM → 创建原型场景 → 三视图排布**。创建独立场景，不删除原场景。

[v0.2.0 发布](https://github.com/ArchitectureWorld/blender-designerBIM/releases/tag/v0.2.0) · [安装包](https://github.com/ArchitectureWorld/blender-designerBIM/releases/download/v0.2.0/designer_bim_p01-0.2.0-blender5.2.2.zip) · [源码包](https://github.com/ArchitectureWorld/blender-designerBIM/releases/download/v0.2.0/designer_bim_p01-0.2.0-source.zip)

## 本轮直接测试这条流程

在新的示例场景中：

| 操作 | 观察 |
|---|---|
| 选 D01 → 复制当前门 → 中心距墙左端 3000 mm | 出现 D04；源门不变，定义仍共享，人工说明不复制 |
| 选 D04 → 精确定位 → 相对移动 +200 mm | 中心成为 3200 mm；墙洞、三维和平立面一起移动 |
| D04 门洞高度设 2400 mm | 仅 D04 增高，立面显示 H 2400；门框截面不拉伸 |
| D04 左右开向切到右铰 | 3D 门扇和平面开启弧切换铰链侧；不镜像整墙 |
| 输入与 D02 重叠的位置，如 4500 mm | 拒绝修改；已有参数和人工说明不改变 |
| D04 添加人工说明，再移动 -100 mm | 保留文字和人工排布位置，提示 REVIEW；只有人工确认才消除 |
| 保存重开，再统一修改门框截面为 80 mm | 新增门、独立尺寸、开向与说明仍在；共享修改不重置门宽门高 |

**新增门**与**复制当前门**是不同操作：新增可输入宽、高和铰链侧；复制继承源门的参数，并建议一个可用位置。位置以墙左端为原点，单位为 mm。这里只支持沿既有直墙的 X 方向定位，不是任意宿主放置。

原有门宽操作、选中／同定义批改、蓝色宽度拖动手柄、人工说明编辑、SVG/JSON 导出继续保留。复制须用插件按钮，不支持原生 Shift+D 后维持工程身份。

## 旧文件兼容

状态 schema 1 读取时迁移为 schema 2，新增 `handing`，默认左铰；保留实例 ID、定义、参数、说明和原有“已复核／待复核”状态，不因版本升级把所有说明误报为待复核。

首次成功写入时，在场景 `dbim_p01_schema1_backup` 中保留原 v1 JSON。读取不会立刻覆盖原状态；下一次编辑或保存才写入 v2。**仍应另存原 .blend 备份**，隐藏 JSON 不是整个项目文件的备份。写入 v2 的文件不可用 v0.1.1 继续编辑；未知未来版本明确拒绝。

## 验证边界

- 纯 Python／静态／分发测试：`python -m pytest -q`。完整结果见 Actions。
- 官方 Blender 5.2.2 CLI 包验证及真实 Blender 操作器、网格、迁移、保存重开：独立 `Blender 5.2.2 runtime` 工作流执行，结果与生成的 `.blend` / SVG 在其 artifacts；脚本存在不等于测试通过。
- **Windows 图形界面的鼠标、对话框、Ctrl+Z、三视图视觉与实际项目交付仍需人工验收。**不能把无界面运行通过说成所有 GUI 通过。
- 用户已确认 v0.1.1 可加载；尚未宣称整条五步运行验收完成。

## 限制

这是毫米参数＋JSON 场景状态原型，尚未接入 Bonsai/IFC 权威数据或正式构件库。不要把 schema 2 视为已稳定的生产资产协议，也不要用于施工图交付。

门洞最小间距／墙端余量 120 mm、门框 15–150 mm 是**原型几何约束，不是建筑规范校核**。门高最高为墙高减120 mm。宽度和高度指门洞，不是净通行尺寸。

本轮统一将三维门扇显示为向 +Y 开启90°，对应平面符号。左右铰链以从 -Y 看墙为准；立面按关闭外形作工程符号表达，并非当前开启姿态的几何投影。不支持内外开四向、自由角度、自动五金或任意墙体。

平立面是门专用参数化表达，不是通用剖切引擎。人工说明过长、非常规尺寸导致图幅拥挤时仍需人工排版；SVG 为 A3、1:25 矢量**测试图**，输出前检查完整图幅。打印须100%，不能“适合页面”。

生成物由参数控制；编辑网格会在刷新时被重建。人工说明可以原位改文字和 G 移动。没有打包字体，没有插件内网络请求或第二套更新器。

## 开发

```bash
python -m pytest -q
python -m compileall -q designer_bim_p01 scripts tests
python scripts/build_release.py --out dist
blender --command extension validate dist/designer_bim_p01-0.2.0-blender5.2.2.zip
blender --background --factory-startup --python-exit-code 1 --python scripts/blender_smoke_test.py -- /tmp/p01-original
blender --background --factory-startup --python-exit-code 1 --python scripts/blender_instances_test.py -- /tmp/p01-instances
```

`core.py`：版本化工程状态；`geometry.py`：三维与平立面生成；`addon.py`：场景、原有交互和持久化；`instance_tools.py`：新增实例编辑入口；`interaction.py`：宽度拖动数值映射。

[本轮设计与边界](docs/superpowers/specs/2026-10-17-instance-edit.md) · [本轮发布说明](docs/releases/v0.2.0.md) · [历史 v0.1.1](docs/releases/v0.1.1.md)。旧 `docs/quickstart.html` 为首次原型指南，新增功能以本页为准。

许可：GPL-3.0-or-later。官方参考：[扩展 CLI](https://docs.blender.org/manual/en/5.2/advanced/command_line/extension_arguments.html)；[5.2 LTS](https://www.blender.org/releases/5-2/)。
