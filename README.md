# DesignerBIM P01 — 整门组件封装

**v0.3.0 · Blender 5.2.2 · 测试候选版，不是生产 BIM 软件。**

本轮修复：门框与门扇不再作为散件平铺到项目场景。外部操作一樘门，进入后才选内部部件；二维图纸仍关联同一工程实例。

## 更新

```text
https://raw.githubusercontent.com/ArchitectureWorld/blender-designerBIM/main/extensions/index.json
```

已安装远程版：另存 `.blend` 备份 → 获取扩展 → 检查更新 → DesignerBIM 0.3.0 → 重启。不添加第二份插件。

第一次使用：添加上述远程存储库并安装；三维视图按 **N → DesignerBIM → 创建原型场景 → 三视图排布**。创建独立场景，不删除原场景。

[v0.3.0发布](https://github.com/ArchitectureWorld/blender-designerBIM/releases/tag/v0.3.0) · [完整验收和限制](docs/releases/v0.3.0.md)

## 本轮先测这五步

| 操作 | 必须观察到 |
|---|---|
| 点击门框或门扇 | 只选中D01一个集合实例；MODEL列表不再平铺门零件 |
| Tab进入内部→选门框→编辑参数→仅当前实例80mm | D01门框80，其他门仍60；二维同步，定义ID仍共享 |
| 退出，在D02内部修改共享门框70mm | D02/D03变70；D01保留局部80；恢复继承后D01也变70 |
| 复制/沿墙定位/删除整门 | 新实例身份独立，墙洞及平立面同步；删除说明必须确认 |
| 保存重开 | 默认回到整门模式；局部参数、身份、图纸关联和说明不丢失 |

三维视图组件快捷键：Tab进入/退出，G沿墙精确定位对话框，Shift+D复制对话框，X/Delete删除确认。非组件对象走Blender原快捷键；混合/多门选择不会偷偷执行单门命令。当前不提供任意空间的自由移动。

组件内部的编辑范围：门框截面、门扇厚度。门框/门扇可单独选中，但必须通过参数编辑。任意网格/拓扑修改尚不支持，检测到此类修改会停止刷新而不是静默覆盖。不要用Make Instances Real、Join、Apply Transform绕过组件系统；Outliner原生删除/复制也不是工程命令，请使用组件按钮或3D View快捷键。

原有门宽/门高、开向、人工说明、SVG/JSON输出继续保留。手工说明是图面内容，不与三维组件一起实体移动；位置保留，关联变化需复核。

## 数据与兼容

JSON仍是本原型权威状态，schema1/2迁移到3。新增门框/门扇的实例级可空覆盖；未覆盖的参数继承共享定义。局部编辑不偷偷拆成新定义。复制继承参数与覆盖，不复制人工说明或已复核状态。

旧散件场景在启用、载入或刷新时封装；schema1/2分别保留 `dbim_p01_schema1_backup` / `dbim_p01_schema2_backup`。它们只是JSON备份，不能代替完整 `.blend` 备份。schema3文件不能用旧插件继续编辑。

MODEL、PLAN、ELEVATION三个代理对应同一door_id，不是三份工程构件。私有集合是每实例的几何/表达缓存，不是独立族定义。本原型尚未定义最终生产库协议，也没有接入IFC。

## 验证

```bash
python -m pytest -q
python -m compileall -q designer_bim_p01 scripts tests
python scripts/build_release.py --out dist
blender --command extension validate dist/designer_bim_p01-0.3.0-blender5.2.2.zip
blender -b --factory-startup --python-exit-code 1 --python scripts/blender_smoke_test.py -- reports/runtime-original
blender -b --factory-startup --python-exit-code 1 --python scripts/blender_instances_test.py -- reports/runtime-instances
blender -b --factory-startup --python-exit-code 1 --python scripts/blender_components_test.py -- reports/runtime-components
```

Blender实际运行结果见Actions，不能把纯逻辑或打包检查当作实机验收。GUI测试使用实际Blender视口选择/组件内部编辑和撤销；不能代替Windows本机鼠标及完整多视图体验验收。

## 开发组织

- `core.py`：稳定实例身份、共享参数/局部覆盖、说明、验证及迁移。
- `geometry.py`：门专用三维/二维生成；不是通用投影/剖切引擎。
- `component_scene.py`：集合实例封装、私有部件、显式内部上下文、网格覆盖保护。
- `component_tools.py`：整门生命周期、内部参数编辑与组件上下文快捷操作。
- `addon.py` / `instance_tools.py`：场景、持久化、视图和实例参数操作。

限制：单面既有直墙、门洞几何约束，不是结构/规范审查；当前原型二维SVG不能直接用于施工。库资产暂不规模化创建。无隐藏联网、上传或任意用户脚本执行。

GPL-3.0-or-later，见LICENSE。两个项目独立，本库不包括铝型材家居平台。
