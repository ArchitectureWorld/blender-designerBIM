# SPDX-License-Identifier: GPL-3.0-or-later
"""Deterministic door geometry and parametric drawings, in millimetres.

These are deliberately explicit door-specific drawings, not a general-purpose
sectioning engine. Three-dimensional geometry and both drawings consume the same
validated engineering state. No images, screenshot tracing, or external assets.
"""
from __future__ import annotations
from dataclasses import dataclass
from html import escape
import math
from . import core


@dataclass(frozen=True)
class Box:
    key: str
    role: str
    door_id: str
    minimum_mm: tuple[float, float, float]
    maximum_mm: tuple[float, float, float]

    @property
    def size_mm(self):
        return tuple(b-a for a, b in zip(self.minimum_mm, self.maximum_mm))

    @property
    def volume_mm3(self):
        return math.prod(self.size_mm)

    @property
    def vertices_mm(self):
        x0,y0,z0 = self.minimum_mm
        x1,y1,z1 = self.maximum_mm
        return ((x0,y0,z0),(x1,y0,z0),(x1,y1,z0),(x0,y1,z0),
                (x0,y0,z1),(x1,y0,z1),(x1,y1,z1),(x0,y1,z1))

    @property
    def faces(self):
        return ((0,3,2,1),(4,5,6,7),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7))


@dataclass(frozen=True)
class Line:
    key: str
    points: tuple[tuple[float,float], ...]
    role: str = 'outline'
    door_id: str = ''
    width_mm: float = 12.0
    closed: bool = False


@dataclass(frozen=True)
class Text:
    key: str
    text: str
    position_mm: tuple[float,float]
    role: str = 'label'
    door_id: str = ''
    size_mm: float = 120.0
    align: str = 'CENTER'
    note_id: str = ''


@dataclass(frozen=True)
class Drawing:
    view: str
    lines: tuple[Line, ...]
    texts: tuple[Text, ...]
    bounds_mm: tuple[float,float,float,float]


def model_parts(m: core.Model) -> tuple[Box, ...]:
    core.validate(m)
    result = []
    depth = m.wall.depth_mm/2
    doors = sorted(m.doors.values(), key=lambda d:d.center_x_mm)
    last = 0.0
    for d in doors:
        left,right = d.center_x_mm-d.width_mm/2,d.center_x_mm+d.width_mm/2
        result.append(Box(f'wall.pier-before-{d.id}', 'wall', '', (last,-depth,0), (left,depth,m.wall.height_mm)))
        result.append(Box(f'wall.head-{d.id}', 'wall', '', (left,-depth,d.height_mm), (right,depth,m.wall.height_mm)))
        f = m.definitions[d.definition_id]
        s,c = f.frame_section_mm,f.clearance_mm
        result.extend((
            Box(f'{d.id}.jamb-left','frame',d.id,(left,-depth,0),(left+s,depth,d.height_mm)),
            Box(f'{d.id}.jamb-right','frame',d.id,(right-s,-depth,0),(right,depth,d.height_mm)),
            Box(f'{d.id}.head','frame',d.id,(left+s,-depth,d.height_mm-s),(right-s,depth,d.height_mm)),
            Box(f'{d.id}.leaf','leaf',d.id,(left+s+c,-depth+c,c),
                (right-s-c,-depth+c+f.leaf_thickness_mm,d.height_mm-s-c)),
        ))
        last = right
    result.append(Box('wall.pier-end','wall','',(last,-depth,0),(m.wall.length_mm,depth,m.wall.height_mm)))
    return tuple(result)


def drawing(m: core.Model, view: str) -> Drawing:
    core.validate(m)
    if view not in ('PLAN','ELEVATION'):
        raise core.ModelError('Unknown drawing view')
    lines, texts = [],[]
    def line(key,pts,role='outline',door_id='',width=12,closed=False):
        lines.append(Line(key,tuple(pts),role,door_id,width,closed))
    def rect(key,x0,y0,x1,y1,role='outline',door_id='',width=12):
        line(key,((x0,y0),(x1,y0),(x1,y1),(x0,y1)),role,door_id,width,True)
    def text(key,body,pos,role='label',door_id='',size=120,align='CENTER',note_id=''):
        texts.append(Text(key,str(body),tuple(pos),role,door_id,size,align,note_id))
    depth = m.wall.depth_mm/2
    if view == 'PLAN':
        for part in model_parts(m):
            if part.role == 'wall' and '.pier-' in part.key:
                x0,y0,_=part.minimum_mm; x1,y1,_=part.maximum_mm
                rect(part.key,x0,y0,x1,y1,'cut',width=22)
        title_y = 1650
    else:
        rect('wall.outer',0,0,m.wall.length_mm,m.wall.height_mm,'outline',width=18)
        title_y = m.wall.height_mm+540
    for d in m.doors.values():
        f=m.definitions[d.definition_id]; s=f.frame_section_mm; c=f.clearance_mm
        left,right=d.center_x_mm-d.width_mm/2,d.center_x_mm+d.width_mm/2
        if view == 'PLAN':
            rect(f'{d.id}.jamb-left',left,-depth,left+s,depth,'cut',d.id,20)
            rect(f'{d.id}.jamb-right',right-s,-depth,right,depth,'cut',d.id,20)
            hx,hy=left+s+c,depth
            radius=d.width_mm-2*s-2*c
            rect(f'{d.id}.open-leaf',hx,hy,hx+f.leaf_thickness_mm,hy+radius,'symbol',d.id,12)
            arc=tuple((hx+radius*math.cos(i*math.pi/64),hy+radius*math.sin(i*math.pi/64)) for i in range(33))
            line(f'{d.id}.swing',arc,'symbol',d.id,8)
            text(f'{d.id}.tag',d.tag,(d.center_x_mm,-190),door_id=d.id,size=100)
            base=-depth
            dim_y=-500
        else:
            rect(f'{d.id}.opening',left,0,right,d.height_mm,'outline',d.id,16)
            rect(f'{d.id}.clear-frame',left+s,0,right-s,d.height_mm-s,'frame',d.id)
            rect(f'{d.id}.leaf',left+s+c,c,right-s-c,d.height_mm-s-c,'symbol',d.id,9)
            text(f'{d.id}.tag',d.tag,(d.center_x_mm,d.height_mm+150),door_id=d.id)
            base=0
            dim_y=-380
        line(f'{d.id}.width-line',((left,dim_y),(right,dim_y)),'dimension',d.id,6)
        for suffix,x in (('left',left),('right',right)):
            line(f'{d.id}.witness-{suffix}',((x,base-40),(x,dim_y-90)),'dimension',d.id,5)
            line(f'{d.id}.tick-{suffix}',((x-45,dim_y-45),(x+45,dim_y+45)),'dimension',d.id,9)
        text(f'{d.id}.width-label',f'{d.width_mm:g}',(d.center_x_mm,dim_y+100),'dimension',d.id)
    for n in m.notes.values():
        if n.view != view:
            continue
        text(f'note.{n.id}',n.text,n.position_mm,'manual',n.door_id,110,'LEFT',n.id)
        d=m.doors[n.door_id]
        target=(d.center_x_mm+d.width_mm/2,d.height_mm if view=='ELEVATION' else depth)
        line(f'note.{n.id}.leader',(n.position_mm,target),'annotation',n.door_id,5)
        if core.note_requires_review(m,n.id):
            text(f'note.{n.id}.review','[REVIEW / 需复核]',(n.position_mm[0],n.position_mm[1]+150),
                 'review',n.door_id,95,'LEFT',n.id)
    text('view.title',f'{view}  /  r{m.revision}',(0,title_y),'title','',170,'LEFT')
    text('view.subtitle','OPENING DIMENSIONS IN mm | P01 TEST DRAWING',
         (0,title_y-200),'subtitle','',90,'LEFT')
    coords=[pt for l in lines for pt in l.points]+[t.position_mm for t in texts]
    bounds=(min(x for x,y in coords)-200,min(y for x,y in coords)-200,
            max(m.wall.length_mm,max(x for x,y in coords))+200,max(y for x,y in coords)+220)
    return Drawing(view,tuple(lines),tuple(texts),bounds)


def svg_document(m: core.Model) -> str:
    """A3 vector review sheet, exact 1:25 dimensions. Not a signed drawing.

    Text is escaped, not executable markup. A fixed sheet makes scale meaningful;
    out-of-sheet manual annotations are reported by the UI rather than rescaled.
    """
    core.validate(m)
    out=['<?xml version="1.0" encoding="UTF-8"?>',
         '<svg xmlns="http://www.w3.org/2000/svg" width="420mm" height="297mm" viewBox="0 0 420 297">',
         '<rect width="420" height="297" fill="white"/>',
         '<style>text{font-family:"Noto Sans CJK SC","Microsoft YaHei",Arial,sans-serif}</style>',
         '<rect x="10" y="10" width="400" height="277" fill="none" stroke="#adb3bb" stroke-width="0.3"/>',
         '<text x="18" y="22" font-size="5.5" fill="#172b40">DesignerBIM / DOOR PROTOTYPE 01</text>',
         f'<text x="18" y="29" font-size="2.8" fill="#5d6874">Blender 5.2.2 target | Schema {m.schema_version} | Revision {m.revision} | 1:25 at 100% print</text>']
    scale=.04
    for view,ox,oy in [('ELEVATION',25,185),('PLAN',25,257)]:
        dr=drawing(m,view)
        heading_y = 43 if view=='ELEVATION' else 209
        out.append(f'<text x="18" y="{heading_y}" font-size="4.5" fill="#172b40">{view} / r{m.revision}</text>')
        out.append(f'<g id="{view.lower()}">')
        for l in dr.lines:
            pts=' '.join(f'{ox+x*scale:.4f},{oy-y*scale:.4f}' for x,y in l.points)
            tag='polygon' if l.closed else 'polyline'
            color='#b35424' if l.role=='annotation' else '#172b40'
            out.append(f'<{tag} id="{view}-{escape(l.key,quote=True)}" data-door-id="{escape(l.door_id,quote=True)}" points="{pts}" fill="none" stroke="{color}" stroke-width="{max(.13,l.width_mm*scale):.3f}"/>')
        for t in dr.texts:
            if t.role in ('title','subtitle'):
                continue
            x,y=t.position_mm
            color='#b33b25' if t.role=='review' else ('#825228' if t.role=='manual' else '#172b40')
            anchor='start' if t.align=='LEFT' else 'middle'
            out.append(f'<text id="{view}-{escape(t.key,quote=True)}" data-door-id="{escape(t.door_id,quote=True)}" x="{ox+x*scale:.3f}" y="{oy-y*scale:.3f}" font-size="{t.size_mm*scale:.2f}" text-anchor="{anchor}" fill="{color}">')
            for idx,body in enumerate(t.text.splitlines() or ['']):
                out.append(f'<tspan x="{ox+x*scale:.3f}" dy="{0 if idx==0 else t.size_mm*scale*1.2:.3f}">{escape(body)}</tspan>')
            out.append('</text>')
        out.append('</g>')
    review=sum(core.note_requires_review(m,nid) for nid in m.notes)
    out.extend([f'<text x="18" y="293" font-size="2.8" fill="#8b3526">PROTOTYPE — not construction documentation | Review notes: {review}</text>', '</svg>'])
    return '\n'.join(out)
