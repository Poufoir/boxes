# Copyright (C) 2013-2023 Florian Festi
#
#   This program is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   This program is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with this program.  If not, see <http://www.gnu.org/licenses/>.

from typing import List
from boxes import edges
from boxes.utils import edge_init
from boxes.lids import _TopEdge, LidSettings


class TopEdge(edges.BaseEdge):
    def __init__(self, boxes, lengths, h):
        super().__init__(boxes, None)
        self.lengths = lengths
        self.h = h

    def __call__(self, length, **kw):
        h = self.h
        t = self.boxes.thickness
        t2 = t * 2**0.5
        slot = h / 2**0.5 + t / 2
        self.polyline(
            0, 90, t2, -45, slot - t, -90, t, -90, slot, 135, self.lengths[0] - t2 / 2
        )

        for l in self.lengths[1:]:
            self.polyline(
                0,
                45,
                t,
                45,
                h / 2 - t2 / 2,
                -90,
                t,
                -90,
                h / 2 - t2,
                135,
                slot - t,
                -90,
                t,
                -90,
                slot,
                135,
                l - t2 / 2,
            )
        self.polyline(t2 / 2)


class SmallPartsTray2(_TopEdge):
    """A Type Tray variant with slopes toward the front"""

    description = """Assemble inside out. If there are inner front to back walls start with attaching the floor boards to them. Then add the vertical inner left to right walls. After sliding in the slopes attach the outer wall to fix everything in place.

If there are no inner front to back walls just add everything to one side wall and then add the other one after that. Possibly saving the front and back as last step."""

    ui_group = "Tray"

    def __init__(
        self,
        x: float = 100,
        y: float = 100,
        h: float = 30,
        sx: str | List = "50*3",
        sy: str | List = "50*3",
        sh: str | List = "50*3",
        hi: float = 0,
        hole_dD: str = "3.5:6.5",
        bottom_edge: str = "h",
        top_edge: str = "e",
        outside: bool = True,
        nema_mount: int = 23,
        thickness: float = 3,
        output: str = "box.svg",
        format: str = "svg",
        tabs: float = 0,
        qr_code: bool = False,
        debug: bool = False,
        labels: bool = True,
        reference: float = 100,
        inner_corners: str = "loop",
        burn: float = 0.1,
        back_height: float = 0,
        radius: float = 0,
        handle: bool = False,
    ) -> None:
        super().__init__(
            x,
            y,
            h,
            sx,
            sy,
            sh,
            hi,
            hole_dD,
            bottom_edge,
            top_edge,
            outside,
            nema_mount,
            thickness,
            output,
            format,
            tabs,
            qr_code,
            debug,
            labels,
            reference,
            inner_corners,
            burn,
        )
        self.addTopEdgeSettings(
            fingerjoint={"surroundingspaces": 1.0}, roundedtriangle={"outset": 1}
        )
        edge_init(self, [LidSettings])
        # additional height of the back wall - e top edge only
        self.back_height = back_height
        # radius for strengthening side walls with back_height
        self.radius = radius
        # add handle to the bottom (changes bottom edge in the front)
        self.handle = handle

    def fingerHolesCB(self, sections, height):
        def CB():
            posx = -0.5 * self.thickness
            for x in sections[:-1]:
                posx += x + self.thickness
                self.fingerHolesAt(posx, 0, height)

        return CB

    def fingerHoleLineCB(self, posx, posy, sections):
        def CB():
            self.moveTo(posx, posy, 90)
            for l in sections:
                self.fingerHolesAt(0, 0, l, 0)
                self.moveTo(l + self.thickness)

        return CB

    def xHoles(self):
        posx = -0.5 * self.thickness
        for x in self.sx[:-1]:
            posx += x + self.thickness
            self.fingerHolesAt(posx, 0, self.hi)

    def yHoles(self):
        t = self.thickness
        posy = -0.5 * self.thickness
        for y in self.sy[:-1]:
            posy += y + self.thickness
            self.fingerHolesAt(posy, 0, self.hi - t * 2**0.5)
            with self.saved_context():
                self.moveTo(posy - 0.5 * t, self.hi, 135)
                self.fingerHolesAt(-0.5 * t, 0, self.hi * 2**0.5 + t / 2)

        self.moveTo(posy + self.sy[-1] + 0.5 * t, self.hi, 135)
        self.fingerHolesAt(-0.5 * t, 0, self.hi * 2**0.5 + t / 2)

    def render(self):
        # tmp settings
        self.top_edge = "e"
        self.bottom_edge = "F"

        if self.outside:
            self.sx = self.adjustSize(self.sx)
            self.sy = self.adjustSize(self.sy)
            self.h = self.adjustSize(self.h, e2=False)
            if self.hi:
                self.hi = self.adjustSize(self.hi, e2=False)

        x = sum(self.sx) + self.thickness * (len(self.sx) - 1)
        y = sum(self.sy) + self.thickness * (len(self.sy) - 1)
        h = self.h
        sameh = not self.hi
        hi = self.hi = self.hi or h
        t = self.thickness

        # outer walls
        b = self.bottom_edge
        tl, tb, tr, tf = self.topEdges(self.top_edge)
        self.closedtop = self.top_edge in "fFhŠ"

        bh = self.back_height if self.top_edge == "e" else 0.0

        # x sides

        self.context.save()

        # outer walls - front/back
        if bh:
            self.rectangularWall(
                x,
                h + bh,
                [b, "f", tb, "f"],
                callback=[self.xHoles],
                # ignore_widths=[],
                move="up",
                label="back",
            )
            self.rectangularWall(
                x,
                h,
                ["f" if self.handle else b, "f", "e", "f"],
                callback=[
                    self.fingerHolesCB(self.sx[::-1], h),
                ],
                move="up",
                label="front",
            )
        else:
            self.rectangularWall(
                x,
                h,
                [b, "F", tb, "F"],
                callback=[self.xHoles],
                # ignore_widths=[1, 6],
                move="up",
                label="back",
            )
            self.rectangularWall(
                x,
                hi - t * 2**0.5,
                ["f" if self.handle else b, "F", "e", "F"],
                callback=[
                    self.fingerHolesCB(self.sx[::-1], hi - t * 2**0.5),
                ],
                # ignore_widths=[] if self.handle else [1, 6],
                move="up",
                label="front",
            )

        # floor boards

        t2 = t * 2**0.5
        dy = hi + t2 / 2
        slot = t + t2 / 2  # 1.5*t
        floors = [self.sy[0] - hi - slot + t2, slot]
        self.rectangularWall(
            x,
            floors[0],
            "ffef",
            callback=[self.fingerHolesCB(self.sx, self.sy[0] - dy)],
            move="up",
            label="floor back side",
        )
        for y_ in self.sy[1:]:
            self.rectangularWall(
                x,
                y_ - slot + t,
                "efef",
                callback=[
                    self.fingerHolesCB(self.sx, y_ - slot + t),
                    self.fingerHoleLineCB(hi - t2 + t / 2, 0, self.sx[::-1]),
                ],
                move="up",
                label="floor",
            )
            floors.extend([y_ - slot + t, slot])
        self.rectangularWall(
            x,
            hi - t2,
            "efYf" if self.handle else "efff",
            callback=[self.fingerHolesCB(self.sx, hi - t2)],
            move="up",
            label="floor front side",
        )
        floors.append(hi - t2)

        # Inner walls

        be = "f" if b != "e" else "e"

        for i in range(len(self.sy) - 1):
            e = [
                edges.SlottedEdge(self, self.sx, be, slots=0.5 * hi),
                "f",
                edges.SlottedEdge(self, self.sx[::-1], "e"),
                "f",
            ]
            self.rectangularWall(x, hi - t2, e, move="up", label=f"inner x {i+1}")
        # slopes
        for i in self.sy:
            self.rectangularWall(
                x,
                hi * 2**0.5 + t / 2,
                [
                    edges.SlottedEdge(self, self.sx, "e", slots=hi / 2**0.5),
                    "f",
                    edges.SlottedEdge(self, self.sx[::-1], "e"),
                    "f",
                ],
                move="up",
                label="slope",
            )

        # top / lid
        self.drawLid(x, y, self.top_edge)  # XXX deal with front
        self.lid(x, y, self.top_edge)

        self.context.restore()
        self.rectangularWall(x, hi, "ffff", move="right only")

        # y walls

        # outer walls - left/right

        for move in ("up", "up mirror"):
            if bh:
                self.trapezoidSideWall(
                    y,
                    h + bh,
                    hi - t * 2**0.5,
                    [
                        edges.CompoundEdge(self, ("FE" * len(self.sy)) + "F", floors),
                        "h",
                        "e",
                        "h",
                    ],
                    radius=self.radius,
                    callback=[
                        self.yHoles,
                    ],
                    move=move,
                    label="side",
                )
            else:
                self.rectangularWall(
                    y,
                    h,
                    [
                        edges.CompoundEdge(self, ("FE" * len(self.sy)) + "F", floors),
                        edges.CompoundEdge(
                            self, "fE", (hi - t * 2**0.5, h - hi + t * 2**0.5)
                        ),
                        tl,
                        "f",
                    ],
                    callback=[
                        self.yHoles,
                    ],
                    # ignore_widths=[6] if self.handle else [1, 6],
                    move=move,
                    label="side",
                )

        # inner walls
        for i in range(len(self.sx) - 1):
            e = [
                edges.CompoundEdge(self, ("fE" * len(self.sy)) + "f", floors),
                edges.CompoundEdge(self, "fe", (hi - t * 2**0.5, t * 2**0.5)),
                TopEdge(self, self.sy[::-1], hi),
                "f",
            ]
            self.rectangularWall(y, hi, e, move="up", label=f"inner y {i+1}")
