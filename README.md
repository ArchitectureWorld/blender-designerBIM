# DesignerBIM P01 — 门组件二维/三维联动原型

**版本：0.1.1｜开发基线：Blender 5.2.2｜状态：测试候选版，尚未完成实机验收。**

这一轮只验证三个门实例的独立宽度、共享门框、平立面尺寸联动、人工说明保护与保存重开。它不是完整 BIM 软件，不是已定版组件库底层，也不改动铝型材或 Revit 项目。

## Blender 远程安装与更新

复制下面的完整地址（不是仓库首页，不是 ZIP 下载页）：

```text
https://raw.githubusercontent.com/ArchitectureWorld/blender-designerBIM/main/extensions/index.json
```

1. Blender 5.2.2 → 编辑 → 偏好设置 → 获取扩展 / Get Extensions；允许在线访问。
2. 打开右上方存储库 / Repositories，点击 `+` → 添加远程存储库 / Add Remote Repository，粘贴上方地址。
3. 刷新后搜索 `DesignerBIM`，安装并启用 **DesignerBIM P01 — Door Lab**。
4. 后续在获取扩展中“检查更新 / Check for Updates”，对该扩展点击更新。地址不变，无须每次下载新 ZIP；不要将“检查更新”理解为已自动替你安装更新。
5. 保存当前文件，在三维视图按 `N` → **DesignerBIM** → **创建原型场景** → **三视图排布**。

本源公开，无须令牌，无须自行启用 GitHub Pages。网络环境仍须能够访问 GitHub Raw 与 Releases。

### 已经从磁盘安装过 v0.1.0

先另存 `.blend` 备份，停用旧的本地 DesignerBIM P01，重启 Blender，再从远程源安装/启用新版。**不要同时启用本地版和远程版**，以免相同操作器、面板和处理器重复注册。确认新版正常后可只卸载旧的 DesignerBIM；不要删除整个本地存储库或其他插件。

### 手动下载备用

- [v0.1.1 发布说明](https://github.com/ArchitectureWorld/blender-designerBIM/releases/tag/v0.1.1)
- [Blender 安装包](https://github.com/ArchitectureWorld/blender-designerBIM/releases/download/v0.1.1/designer_bim_p01-0.1.1-blender5.2.2.zip)
- [完整源码包](https://github.com/ArchitectureWorld/blender-designerBIM/releases/download/v0.1.1/designer_bim_p01-0.1.1-source.zip)
- [安装与验收指南源码](docs/quickstart.html)

从磁盘安装的副本属于本地存储库，不会因为后来添加了远程源就自动变成远程管理副本。

## 五步验收

| 步骤 | 操作 | 必须观察到 |
|---|---|---|
| 1 | 选 D01，修改门洞宽度 900 → 1200，范围“只改当前实例” | D01 的三维、平面、立面和尺寸变化；D02/D03 仍 900；框截面仍 60 |
| 2 | 统一修改共享门框 60 → 80 | 三樘门框都变化；门洞宽度仍为 1200、900、900 |
| 3 | 选 D02，添加“人工收口说明”，所属视图选立面 | 立面出现可编辑说明；三维、二维对象都指向 D02 的同一实例 ID |
| 4 | 把 D02 宽度改为 1100 | 说明文字与人工摆放位置保留；出现 REVIEW / 需复核；只有人工确认才清除 |
| 5 | 保存 `.blend`，关闭重开，再改 D03 宽度 | 实例关联、二维尺寸、说明及复核状态不丢失；仍可继续修改 |

补充鼠标验收：蓝色右向箭头仅调整当前门宽，门中心不动；默认 10mm 步进，Shift 为 1mm，Esc/右键取消；完成后 Ctrl+Z 撤销。**拖动、取消、撤销及自动分屏尚未在 Blender 中验证。**

## 已实现的代码范围

- 毫米单位的纯 Python 状态模型，稳定的定义/门实例/人工说明 ID；JSON schema 1，不自动吞掉未知版本。
- 确定性墙体分段生成真实门洞，不是把门矩形贴在完整墙上。门框截面与门洞宽度分别控制。
- 独立实例、选中实例批改、同定义实例批改；选中批改不偷偷创建新的联动类型。
- 门参数生成平面、立面与真实门洞宽度尺寸；这是门专用的二维表达，不是任意三维模型剖切。
- 人工说明文本/XY位置单独保存，在刷新、参数修改与保存前采集。相关实例、定义或宿主参数变化触发复核。
- Blender 侧栏、宽度拖动、独立示例场景、三视图布局、SVG/JSON 用户指定路径导出。
- A3、1:25 的矢量 SVG 测试图；网页预览中的图来自这个生成器，不是 Blender 截图。

## 已验证 / 未验证

原始 v0.1.0 已运行 **33 项**纯逻辑/静态测试；v0.1.1 加入 **10 项**分发测试，本次准备阶段 `python -m pytest -q` 共 **43 项通过**。包括状态转换、几何体积和尺寸、稳定 ID、二维尺寸、SVG转义/布局、拖动数值映射与包元数据/语法检查。所有 Python 文件通过编译检查；两张实际 SVG 已渲染并检查，修复了页脚碰撞和默认引线穿过门编号的问题。

**未运行：Blender 5.2.2 安装/注册、实际网格生成、侧栏/鼠标/撤销/分屏、`.blend` 保存重开、官方 extension validate。**开发容器没有 Blender/bpy，两台连接开发机访问失败，运行包获取也未成功。脚本或测试的存在不等于已经跑过。当前不能标记为“五步验收通过”。

## 重要限制

- 仅一面直墙、三个预置门、固定门高与位置。不是任意墙体开洞工具；目前不支持原生 Shift+D 复制、原生变换或任意网格编辑后保持工程关联。
- 请用本插件的参数入口修改门。生成的部件锁定变换；进入编辑模式修改其网格会在刷新时被重新生成。人工说明可原位编辑文本和 G 移动位置；删除说明的独立工作流尚未实现。
- 当前是 JSON 场景状态原型，**尚未接入 Bonsai/IFC 权威数据、工程族库、通用图模引擎或施工图发布系统**。不要把 schema 1 当成最终生产库标准。
- 默认墙垛最小 120mm、门框15—150mm等是测试模型的几何边界，不是建筑规范判定。
- 尺寸是**门洞宽**，不是扣除框/缝后的有效通行宽。平面开启弧是符号表达，三维门扇采用关闭姿态。
- 人工说明过长或移出图幅需要人工排版，尚无通用自动避让/分页。SVG测试图不用于施工；打印必须100%，不要“适合页面”。
- 中文三维文本尝试使用用户系统已有字体；未打包任何字体文件。系统没有可加载的中文字体时，三维文本可能缺字，侧栏和SVG字体回退另行处理。
- 扩展声明最低 5.2.2、排除 5.3+。其他 5.2 补丁也未验证；实机验收脚本只接受精确的 5.2.2。

## 开发者测试

纯 Python：

```bash
python -m pip install pytest
python -m pytest -q tests
```

Blender 运行测试（新进程，使用 factory-startup，不要对生产文件运行）：

```bash
blender --background --factory-startup --python-exit-code 1 --python scripts/blender_smoke_test.py -- reports/blender-runtime
```

Windows 也可调用 `scripts/run_blender_tests.ps1 -BlenderExe '实际的blender.exe路径'`。结果写入 `reports/blender-runtime/runtime-result.json`。脚本检查真实网格、操作器、注释、故障回退、保存重开；鼠标和布局仍须手动验收。

生成 `.blend`：

```bash
blender --background --factory-startup --python-exit-code 1 --python scripts/create_demo.py -- samples/DesignerBIM_P01.blend
```

官方安装包验证（本环境未运行）：

```bash
blender --command extension validate designer_bim_p01-0.1.1-blender5.2.2.zip
```

## 源码组织与接续

`core.py` 是工程状态；`geometry.py` 生成三维几何和二维表达；`interaction.py` 将拖动转换为宽度；`addon.py` 是 Blender 界面/持久化适配层。`samples` 是实际纯逻辑输出；`reports` 保留红/绿测试和当前验证边界。

后续先完成 Blender 5.2.2 实机验收并处理报错，再扩展“路径风管/连接”验证。不要在当前原型直接大规模建库。源码与发布工作流现在由本仓库管理，版本包通过 GitHub Releases 分发。

许可：GPL-3.0-or-later，见 LICENSE。无网络调用、无上传、无任意用户脚本执行。

## 官方参考（原型参考，按目标版本另行实机核验）

- Blender 5.2 LTS / 5.2.2：https://www.blender.org/releases/5-2/
- Blender 5.2 API / Gizmo：https://docs.blender.org/api/5.2/bpy.types.Gizmo.html
- Blender 5.2 API / Mesh：https://docs.blender.org/api/5.2/bpy.types.Mesh.html
- 扩展打包与验证：https://docs.staging.blender.org/manual/en/latest/advanced/extensions/getting_started.html
- 从磁盘安装：https://docs.staging.blender.org/manual/en/latest/editors/preferences/addons.html
