# SPDX-License-Identifier: GPL-3.0-or-later
"""Versioned millimetre-domain model. No Blender state or executable payloads.

Edits return a new validated model. A failed edit never mutates its input.
Definition parameters and occurrence dimensions are deliberately separate.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass, replace
import hashlib
import json
import math
from typing import Iterable
from uuid import uuid4

SCHEMA_VERSION = 3


class ModelError(ValueError):
    """A rejected engineering-state edit; safe to display to the user."""


@dataclass(frozen=True)
class Wall:
    id: str = 'wall-01'
    length_mm: float = 9000.0
    height_mm: float = 3000.0
    depth_mm: float = 200.0


@dataclass(frozen=True)
class DoorDefinition:
    id: str
    name: str = 'P01 Single leaf door'
    frame_section_mm: float = 60.0
    leaf_thickness_mm: float = 40.0
    clearance_mm: float = 8.0


@dataclass(frozen=True)
class DoorInstance:
    id: str
    definition_id: str
    tag: str
    center_x_mm: float
    width_mm: float = 900.0
    height_mm: float = 2100.0
    wall_id: str = 'wall-01'
    handing: str = 'LEFT'
    frame_section_override_mm: float | None = None
    leaf_thickness_override_mm: float | None = None


@dataclass(frozen=True)
class Note:
    id: str
    door_id: str
    text: str
    view: str
    position_mm: tuple[float, float]
    reviewed_signature: str


@dataclass(frozen=True)
class Model:
    schema_version: int
    revision: int
    wall: Wall
    definitions: dict[str, DoorDefinition]
    doors: dict[str, DoorInstance]
    notes: dict[str, Note]


def _finite_positive(value: float, name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
        raise ModelError(f'{name}: requires a finite positive number / 需要有限正数')


def validate(m: Model) -> Model:
    if m.schema_version != SCHEMA_VERSION:
        raise ModelError(f'Unsupported schema {m.schema_version}; current schema is {SCHEMA_VERSION}. 原文件未修改。')
    if not isinstance(m.revision, int) or m.revision < 0:
        raise ModelError('Invalid revision')
    for key in ('length_mm', 'height_mm', 'depth_mm'):
        _finite_positive(getattr(m.wall, key), key)
    if not m.wall.id or not m.definitions:
        raise ModelError('Wall, definition and instance identities are required')
    tags = set()
    for key, d in m.definitions.items():
        if key != d.id or not key:
            raise ModelError('Definition ID mismatch')
        for prop in ('frame_section_mm', 'leaf_thickness_mm', 'clearance_mm'):
            _finite_positive(getattr(d, prop), prop)
        if not 15 <= d.frame_section_mm <= 150:
            raise ModelError('Frame section / 门框截面须在 15–150 mm 内')
        if d.leaf_thickness_mm > m.wall.depth_mm:
            raise ModelError('Leaf thicker than host wall')
    intervals = []
    for key, d in m.doors.items():
        if key != d.id or not key or d.definition_id not in m.definitions or d.wall_id != m.wall.id:
            raise ModelError('Invalid definition/host reference / 构件定义或宿主关联无效')
        if d.handing not in ('LEFT', 'RIGHT'):
            raise ModelError('Handing must be LEFT or RIGHT / 开向须为左铰或右铰')
        if not d.tag or d.tag in tags:
            raise ModelError('Door tags must be unique')
        tags.add(d.tag)
        for prop in ('width_mm', 'height_mm', 'center_x_mm'):
            _finite_positive(getattr(d, prop), prop)
        for override in ('frame_section_override_mm', 'leaf_thickness_override_mm'):
            value = getattr(d, override)
            if value is not None:
                _finite_positive(value, override)
        definition = effective_definition(m, d.id)
        if not 15 <= definition.frame_section_mm <= 150:
            raise ModelError('Local frame section must be 15–150 mm')
        if definition.leaf_thickness_mm > m.wall.depth_mm:
            raise ModelError('Local leaf thicker than host wall')
        if d.width_mm < 300 or d.width_mm <= 2*definition.frame_section_mm+2*definition.clearance_mm+100:
            raise ModelError('Opening too small for frame and leaf / 门洞不足以容纳门框与门扇')
        if d.height_mm < 500 or d.height_mm > m.wall.height_mm-120:
            raise ModelError('Door height outside supported wall range')
        left, right = d.center_x_mm-d.width_mm/2, d.center_x_mm+d.width_mm/2
        if left < 120 or right > m.wall.length_mm-120:
            raise ModelError('Opening exceeds wall margin / 门洞超出墙体边界')
        intervals.append((left, right))
    intervals.sort()
    for a, b in zip(intervals, intervals[1:]):
        if b[0]-a[1] < 120:
            raise ModelError('Openings overlap or pier <120 mm / 门洞重叠或墙垛不足120 mm（原型几何限制，非规范校核）')
    for key, n in m.notes.items():
        if key != n.id or n.door_id not in m.doors or n.view not in ('PLAN', 'ELEVATION'):
            raise ModelError('Invalid note reference')
        if not isinstance(n.text, str) or len(n.text) > 4000:
            raise ModelError('Note text must be <=4000 characters')
        if len(n.position_mm) != 2 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in n.position_mm):
            raise ModelError('Invalid annotation position')
    return m


def demo_model() -> Model:
    definition = DoorDefinition('door-def-01')
    doors = {f'door-0{i}': DoorInstance(f'door-0{i}', definition.id, f'D0{i}', x)
             for i, x in enumerate((1750.0, 4500.0, 7250.0), start=1)}
    return validate(Model(SCHEMA_VERSION, 0, Wall(), {definition.id: definition}, doors, {}))


def dumps(m: Model) -> str:
    validate(m)
    return json.dumps(asdict(m), ensure_ascii=False, sort_keys=True, separators=(',', ':'), allow_nan=False)


def loads(text: str) -> Model:
    try:
        raw = json.loads(text)
        if not isinstance(raw, dict) or raw.get('schema_version') not in (1, 2, SCHEMA_VERSION):
            raise ModelError(f"Unsupported schema {raw.get('schema_version') if isinstance(raw,dict) else '?'}")
        notes = {}
        for key, value in raw['notes'].items():
            value = dict(value)
            value['position_mm'] = tuple(value['position_mm'])
            notes[key] = Note(**value)
        m = validate(Model(SCHEMA_VERSION, raw['revision'], Wall(**raw['wall']),
                           {k: DoorDefinition(**v) for k, v in raw['definitions'].items()},
                           {k: DoorInstance(**v) for k, v in raw['doors'].items()}, notes))
        if raw['schema_version'] in (1, 2):
            # Preserve reviewed/stale state, not just text. New defaults must not
            # turn every previously reviewed annotation into a false warning.
            migrated = {}
            for key, note in notes.items():
                old_signature = signature(m, note.door_id, source_schema=raw['schema_version'])
                reviewed = signature(m, note.door_id) if note.reviewed_signature == old_signature else note.reviewed_signature
                migrated[key] = replace(note, reviewed_signature=reviewed)
            m = replace(m, notes=migrated)
        return m
    except ModelError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError) as exc:
        raise ModelError(f'Invalid project state / 项目状态无效: {exc}') from exc


def affected_ids(m: Model, door_id: str, scope: str = 'INSTANCE', selected_ids: Iterable[str] = ()) -> tuple[str, ...]:
    if door_id not in m.doors:
        raise ModelError('Select a valid door / 请先选择门实例')
    if scope == 'INSTANCE':
        return (door_id,)
    if scope == 'DEFINITION':
        definition_id = m.doors[door_id].definition_id
        return tuple(d.id for d in m.doors.values() if d.definition_id == definition_id)
    if scope == 'SELECTED':
        ids = tuple(dict.fromkeys(selected_ids))
        if not ids or any(k not in m.doors for k in ids):
            raise ModelError('Select at least one valid door / 请先选中有效门实例')
        return ids
    raise ModelError(f'Unknown edit scope: {scope}')


def set_width(m: Model, door_id: str, width_mm: float, *, scope: str = 'INSTANCE', selected_ids: Iterable[str] = ()) -> Model:
    _finite_positive(width_mm, 'width_mm')
    ids = affected_ids(m, door_id, scope, selected_ids)
    if all(m.doors[k].width_mm == width_mm for k in ids):
        return m
    doors = dict(m.doors)
    for key in ids:
        doors[key] = replace(doors[key], width_mm=float(width_mm))
    return validate(replace(m, doors=doors, revision=m.revision+1))


def set_frame_section(m: Model, definition_id: str, value_mm: float) -> Model:
    _finite_positive(value_mm, 'frame_section_mm')
    if definition_id not in m.definitions:
        raise ModelError('Unknown definition')
    if m.definitions[definition_id].frame_section_mm == value_mm:
        return m
    definitions = dict(m.definitions)
    definitions[definition_id] = replace(definitions[definition_id], frame_section_mm=float(value_mm))
    return validate(replace(m, definitions=definitions, revision=m.revision+1))


def signature(m: Model, door_id: str, *, legacy: bool = False, source_schema: int | None = None) -> str:
    door = m.doors[door_id]
    data = {'instance': asdict(door), 'definition': asdict(m.definitions[door.definition_id]), 'host': asdict(m.wall)}
    if legacy or source_schema in (1, 2):
        data['instance'].pop('frame_section_override_mm', None)
        data['instance'].pop('leaf_thickness_override_mm', None)
    if legacy or source_schema == 1:
        data['instance'].pop('handing', None)
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()[:24]


def note_requires_review(m: Model, note_id: str) -> bool:
    note = m.notes[note_id]
    return note.reviewed_signature != signature(m, note.door_id)


def add_note(m: Model, door_id: str, text: str, *, view: str = 'ELEVATION', position_mm: tuple[float, float] | None = None,
             note_id: str | None = None) -> Model:
    if door_id not in m.doors:
        raise ModelError('Unknown annotation target')
    key = note_id or str(uuid4())
    if key in m.notes:
        raise ModelError('Duplicate note ID')
    d = m.doors[door_id]
    pos = position_mm or (d.center_x_mm, d.height_mm+400 if view == 'ELEVATION' else 1100)
    note = Note(key, door_id, text, view, tuple(pos), signature(m, door_id))
    notes = dict(m.notes)
    notes[key] = note
    return validate(replace(m, notes=notes, revision=m.revision+1))


def edit_note(m: Model, note_id: str, *, text: str | None = None, position_mm: tuple[float, float] | None = None) -> Model:
    if note_id not in m.notes:
        raise ModelError('Unknown note ID')
    old = m.notes[note_id]
    new = replace(old, text=old.text if text is None else text,
                  position_mm=old.position_mm if position_mm is None else tuple(position_mm))
    if old == new:
        return m
    notes = dict(m.notes)
    notes[note_id] = new
    return validate(replace(m, notes=notes, revision=m.revision+1))


def confirm_note(m: Model, note_id: str) -> Model:
    if note_id not in m.notes:
        raise ModelError('Unknown note ID')
    n = m.notes[note_id]
    notes = dict(m.notes)
    notes[note_id] = replace(n, reviewed_signature=signature(m, n.door_id))
    return replace(m, notes=notes, revision=m.revision+1)


# Instance editing: units are millimetres; positions refer to the wall's left end.
# These 120 mm gaps are prototype geometry limits, NOT structural/code approval.
def _door(m: Model, door_id: str) -> DoorInstance:
    if door_id not in m.doors:
        raise ModelError('Unknown door / 请先选择有效门实例')
    return m.doors[door_id]


def _replace_door(m: Model, door: DoorInstance) -> Model:
    if m.doors.get(door.id) == door:
        return m
    doors = dict(m.doors)
    doors[door.id] = door
    return validate(replace(m, doors=doors, revision=m.revision+1))


def next_door_tag(m: Model) -> str:
    used = {d.tag for d in m.doors.values()}
    number = max((int(t[1:]) for t in used if t.startswith('D') and t[1:].isdigit()), default=0)+1
    while f'D{number:02d}' in used:
        number += 1
    return f'D{number:02d}'


def add_door(m: Model, definition_id: str, center_x_mm: float, *, width_mm: float = 900,
             height_mm: float = 2100, handing: str = 'LEFT', instance_id: str | None = None) -> Model:
    if definition_id not in m.definitions:
        raise ModelError('Unknown shared definition / 组件定义不存在')
    _finite_positive(center_x_mm, 'center_x_mm')
    _finite_positive(width_mm, 'width_mm')
    _finite_positive(height_mm, 'height_mm')
    key = str(uuid4()) if instance_id is None else instance_id
    if not isinstance(key, str) or not key or key in m.doors:
        raise ModelError('Duplicate or invalid instance ID / 实例标识冲突')
    door = DoorInstance(key, definition_id, next_door_tag(m), float(center_x_mm),
                        float(width_mm), float(height_mm), m.wall.id, handing)
    return _replace_door(m, door)


def copy_door(m: Model, door_id: str, center_x_mm: float, *, instance_id: str | None = None) -> Model:
    source = _door(m, door_id)
    _finite_positive(center_x_mm, 'center_x_mm')
    key = str(uuid4()) if instance_id is None else instance_id
    if not isinstance(key, str) or not key or key in m.doors:
        raise ModelError('Duplicate or invalid instance ID / 实例标识冲突')
    # Validate only after carrying all local overrides into the new occurrence.
    door = replace(source, id=key, tag=next_door_tag(m), center_x_mm=float(center_x_mm))
    return _replace_door(m, door)

def suggest_center(m: Model, width_mm: float, *, preferred_mm: float | None = None) -> float:
    _finite_positive(width_mm, 'width_mm')
    if preferred_mm is not None and (isinstance(preferred_mm, bool) or not isinstance(preferred_mm, (int,float)) or not math.isfinite(preferred_mm)):
        raise ModelError('Invalid preferred location')
    half = width_mm/2
    lower = 120.0
    candidates = []
    intervals = sorted((d.center_x_mm-d.width_mm/2, d.center_x_mm+d.width_mm/2) for d in m.doors.values())
    for left, right in intervals + [(m.wall.length_mm, m.wall.length_mm)]:
        lo, hi = lower+half, left-120-half
        if lo <= hi:
            candidates.append(lo if preferred_mm is None else min(hi, max(lo, preferred_mm)))
        lower = right+120
    if not candidates:
        raise ModelError('No free position for this width / 墙上没有可容纳此门宽的空位')
    return min(candidates, key=lambda x: (abs(x-preferred_mm), x < preferred_mm, x)) if preferred_mm is not None else candidates[0]


def move_door(m: Model, door_id: str, center_x_mm: float) -> Model:
    _finite_positive(center_x_mm, 'center_x_mm')
    return _replace_door(m, replace(_door(m, door_id), center_x_mm=float(center_x_mm)))


def set_height(m: Model, door_id: str, height_mm: float, *, scope: str = 'INSTANCE',
               selected_ids: Iterable[str] = ()) -> Model:
    _finite_positive(height_mm, 'height_mm')
    ids = affected_ids(m, door_id, scope, selected_ids)
    if all(m.doors[k].height_mm == height_mm for k in ids):
        return m
    doors = dict(m.doors)
    for key in ids:
        doors[key] = replace(doors[key], height_mm=float(height_mm))
    return validate(replace(m, doors=doors, revision=m.revision+1))


def set_handing(m: Model, door_id: str, handing: str) -> Model:
    if handing not in ('LEFT', 'RIGHT'):
        raise ModelError('Handing must be LEFT or RIGHT / 开向须为左铰或右铰')
    return _replace_door(m, replace(_door(m, door_id), handing=handing))


# Component parameters are shared rules plus explicit occurrence overrides.
# The occurrence never changes definition_id merely because it has a local value.
_PART_FIELDS = {'FRAME': ('frame_section_mm', 'frame_section_override_mm'),
                'LEAF': ('leaf_thickness_mm', 'leaf_thickness_override_mm')}


def effective_definition(m: Model, door_id: str) -> DoorDefinition:
    d = _door(m, door_id)
    f = m.definitions[d.definition_id]
    return replace(f,
        frame_section_mm=f.frame_section_mm if d.frame_section_override_mm is None else d.frame_section_override_mm,
        leaf_thickness_mm=f.leaf_thickness_mm if d.leaf_thickness_override_mm is None else d.leaf_thickness_override_mm)


def set_component_part(m: Model, door_id: str, part: str, value_mm: float, *, scope: str) -> Model:
    d = _door(m, door_id)
    if part not in _PART_FIELDS or scope not in ('INSTANCE', 'DEFINITION'):
        raise ModelError('Choose FRAME/LEAF and INSTANCE/DEFINITION explicitly')
    _finite_positive(value_mm, 'component part')
    shared, local = _PART_FIELDS[part]
    if scope == 'INSTANCE':
        return _replace_door(m, replace(d, **{local: float(value_mm)}))
    f = m.definitions[d.definition_id]
    if getattr(f, shared) == value_mm:
        return m
    definitions = dict(m.definitions)
    definitions[f.id] = replace(f, **{shared: float(value_mm)})
    return validate(replace(m, definitions=definitions, revision=m.revision+1))


def reset_component_part(m: Model, door_id: str, part: str) -> Model:
    if part not in _PART_FIELDS:
        raise ModelError('Unknown component part')
    return _replace_door(m, replace(_door(m, door_id), **{_PART_FIELDS[part][1]: None}))


def delete_doors(m: Model, door_ids: Iterable[str], *, delete_notes: bool = False) -> Model:
    ids = set(door_ids)
    if not ids or not ids <= m.doors.keys():
        raise ModelError('Select existing door instances to delete')
    notes = {k:n for k,n in m.notes.items() if n.door_id not in ids}
    if len(notes) != len(m.notes) and not delete_notes:
        raise ModelError('门包含人工说明；须明确确认同时删除关联说明')
    return validate(replace(m, doors={k:d for k,d in m.doors.items() if k not in ids},
                            notes=notes, revision=m.revision+1))
