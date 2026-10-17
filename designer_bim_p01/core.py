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

SCHEMA_VERSION = 1


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
    if not m.wall.id or not m.definitions or not m.doors:
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
        if not d.tag or d.tag in tags:
            raise ModelError('Door tags must be unique')
        tags.add(d.tag)
        for prop in ('width_mm', 'height_mm', 'center_x_mm'):
            _finite_positive(getattr(d, prop), prop)
        definition = m.definitions[d.definition_id]
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
        if not isinstance(raw, dict) or raw.get('schema_version') != SCHEMA_VERSION:
            raise ModelError(f"Unsupported schema {raw.get('schema_version') if isinstance(raw,dict) else '?'}")
        notes = {}
        for key, value in raw['notes'].items():
            value = dict(value)
            value['position_mm'] = tuple(value['position_mm'])
            notes[key] = Note(**value)
        return validate(Model(raw['schema_version'], raw['revision'], Wall(**raw['wall']),
                              {k: DoorDefinition(**v) for k, v in raw['definitions'].items()},
                              {k: DoorInstance(**v) for k, v in raw['doors'].items()}, notes))
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


def signature(m: Model, door_id: str) -> str:
    door = m.doors[door_id]
    data = {'instance': asdict(door), 'definition': asdict(m.definitions[door.definition_id]), 'host': asdict(m.wall)}
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
