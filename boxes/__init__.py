#!/usr/bin/env python3
# Copyright (C) 2013-2014 Florian Festi
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
from __future__ import annotations

import copy
import math
import random
import sys
import qrcode
import gettext

from typing import Any, Dict, Tuple, Optional, Union, List
from contextlib import contextmanager
from shapely.geometry import Polygon, Point, LineString
from shapely.ops import split

from boxes import formats, gears, parts, pulley, svgutil
from boxes.Color import Color
from boxes.vectors import kerf
from boxes.qrcode_factory import BoxesQrCodeFactory
from boxes.utils import dist, restore, holeCol
from boxes.settings import HexHolesSettings, Settings
import boxes.edges as edges
from boxes.lids import LidSettings, Lid

#############################################################################
### Building blocks
#############################################################################


class NutHole:
    """Draw a hex nut"""

    sizes: Dict[str, Tuple[float, float]] = {
        "M1.6": (3.2, 1.3),
        "M2": (4, 1.6),
        "M2.5": (5, 2.0),
        "M3": (5.5, 2.4),
        "M4": (7, 3.2),
        "M5": (8, 4.7),
        "M6": (10, 5.2),
        "M8": (13.7, 6.8),
        "M10": (16, 8.4),
        "M12": (18, 10.8),
        "M14": (21, 12.8),
        "M16": (24, 14.8),
        "M20": (30, 18.0),
        "M24": (36, 21.5),
        "M30": (46, 25.6),
        "M36": (55, 31),
        "M42": (65, 34),
        "M48": (75, 38),
        "M56": (85, 45),
        "M64": (95, 51),
    }

    def __init__(self, boxes: Boxes, settings: Settings) -> None:
        self.boxes = boxes
        self.context = boxes.context
        self.settings = settings

    def __getattr__(self, name):
        return getattr(self.boxes, name)

    @restore
    @holeCol
    def __call__(self, size, x=0, y=0, angle=0):
        size = self.sizes.get(size, (size,))[0]
        side = size / 3**0.5
        self.boxes.moveTo(x, y, angle)
        self.boxes.moveTo(-0.5 * side, 0.5 * size, angle)
        for i in range(6):
            self.boxes.edge(side)
            self.boxes.corner(-60)


##############################################################################
### Main class
##############################################################################


class Boxes:
    """Main class -- Generator should subclass this"""

    webinterface: bool = True
    ui_group: str = "Misc"
    UI: str = ""

    description: str = ""  # Markdown syntax is supported

    def __init__(
        self,
        thickness: float = 3,
        output: str = "box.svg",
        format: str = "svg",
        tabs: float = 0.0,
        qr_code: bool = False,
        debug: bool = False,
        labels: bool = True,
        reference: float = 100,
        inner_corners: str = "loop",
        burn: float = 0.1,
    ) -> None:
        self.thickness = thickness
        self.output = output
        self.format = format
        self.tabs = tabs
        self.qr_code = qr_code
        self.debug = debug
        self.labels = labels
        self.reference = reference
        self.inner_corners = inner_corners
        self.burn = burn

        self.formats = formats.Formats()
        self.context = None
        description: str = self.__doc__ or ""
        if self.description:
            description += "\n\n" + self.description
        self.edgesettings: dict[Any, Any] = {}
        self.inkscapefile = None
        self.translations = gettext.NullTranslations()

        self.metadata = {
            "name": self.__class__.__name__,
            "short_description": self.__doc__,
            "description": self.description,
            "group": self.ui_group,
            "url": "",
            "url_short": "",
            "cli": "",
            "cli_short": "",
        }

    @contextmanager
    def saved_context(self):
        """
        Generator: for saving and restoring contexts.
        """
        cr = self.context
        cr.save()
        try:
            yield cr
        finally:
            cr.restore()

    def set_source_color(self, color: Color) -> None:
        """Sets the color of the pen.

        Args:
            color (Color): The color to use
        """

        self.context.set_source_rgb(*color)

    def set_font(self, style: str, bold=False, italic=False):
        """Set font style used

        Args:
            style (str): "serif", "sans-serif" or "monospaced"
            bold (bool, optional): Use bold font. Defaults to False.
            italic (bool, optional): Use italic font. Defaults to False.
        """

        self.context.set_font(style, bold, italic)

    def open(self):
        """
        Prepare for rendering

        Create canvas and edge and other objects
        Call this before .render()
        """
        if self.context is not None:
            return

        self.bedBoltSettings = (3, 5.5, 2, 20, 15)  # d, d_nut, h_nut, l, l1
        self.surface, self.context = self.formats.getSurface(self.format, self.output)

        if self.format == "svg_Ponoko":
            self.context.set_line_width(0.01)
            self.set_source_color(Color.INNER_CUT)
        else:
            self.context.set_line_width(max(2 * self.burn, 0.05))
            self.set_source_color(Color.OUTER_CUT)

        self.spacing = 2 * self.burn + 0.5 * self.thickness
        self.set_font("sans-serif")
        self._buildObjects()
        if self.reference and self.format != "svg_Ponoko":
            self.move(self.reference, 10, "up", before=True)
            self.context.rectangle(0, 0, self.reference, 10)
            if self.reference < 80:
                x_param = self.reference + 5
                align_param = "middle left"
            else:
                x_param = self.reference / 2.0
                align_param = "middle center"
            self.text(
                f"{self.reference:.2f}mm, burn:{self.burn:.2f}mm",
                x_param,
                5,
                fontsize=8,
                align=align_param,
                color=Color.ANNOTATIONS,
            )
            self.move(self.reference, 10, "up")
            if self.qr_code:
                self.renderQrCode()
            self.context.stroke()

    def renderQrCode(self):
        content = self.metadata["url_short"] or self.metadata["cli_short"]
        size = 1.5
        if content:
            with self.saved_context():
                self.qrcode(content, box_size=size, move="right")
                self.text(text=content, y=6, color=Color.ANNOTATIONS, fontsize=6)
            self.qrcode(content, box_size=size, move="up only")

    def addPart(self, part: Union[Boxes, edges.BaseEdge], name: Optional[str] = None):
        """Add Edge or other part instance to this one and add it as attribute

        Args:
            part (Union[Boxes, edges.BaseEdge]): Part to be added
            name (Optional[str], optional): name of the part. Defaults to None.
        """
        if name is None:
            name = part.__class__.__name__
            name = name[0].lower() + name[1:]
        # if not hasattr(self, name):
        if isinstance(part, edges.BaseEdge):
            self.edges[part.char] = part
        else:
            setattr(self, name, part)

    def addParts(self, parts: List[Union[Boxes, edges.BaseEdge]]):
        for part in parts:
            self.addPart(part)

    def _buildObjects(self):
        """Add default edges and parts"""
        self.edges = {}
        self.addPart(edges.Edge(self, None))
        self.addPart(edges.OutSetEdge(self, None))
        edges.GripSettings(self.thickness).edgeObjects(self)

        # Finger joints
        # Share settings object
        s = edges.FingerJointSettings(
            self.thickness, True, **self.edgesettings.get("FingerJoint", {})
        )
        s.edgeObjects(self)
        self.addPart(edges.FingerHoles(self, s), name="fingerHolesAt")
        # Stackable
        edges.StackableSettings(
            self.thickness, True, **self.edgesettings.get("Stackable", {})
        ).edgeObjects(self)
        # Dove tail joints
        edges.DoveTailSettings(
            self.thickness, True, **self.edgesettings.get("DoveTail", {})
        ).edgeObjects(self)
        # Flex
        s = edges.FlexSettings(
            self.thickness, True, **self.edgesettings.get("Flex", {})
        )
        self.addPart(edges.FlexEdge(self, s))
        # Clickable
        edges.ClickSettings(
            self.thickness, True, **self.edgesettings.get("Click", {})
        ).edgeObjects(self)
        # Hinges
        edges.HingeSettings(
            self.thickness, True, **self.edgesettings.get("Hinge", {})
        ).edgeObjects(self)
        edges.ChestHingeSettings(
            self.thickness, True, **self.edgesettings.get("ChestHinge", {})
        ).edgeObjects(self)
        edges.CabinetHingeSettings(
            self.thickness, True, **self.edgesettings.get("CabinetHinge", {})
        ).edgeObjects(self)
        # Sliding Lid
        edges.SlideOnLidSettings(
            self.thickness, True, **self.edgesettings.get("SlideOnLid", {})
        ).edgeObjects(self)
        # Rounded Triangle Edge
        edges.RoundedTriangleEdgeSettings(
            self.thickness, True, **self.edgesettings.get("RoundedTriangleEdge", {})
        ).edgeObjects(self)
        # Grooved Edge
        edges.GroovedSettings(
            self.thickness, True, **self.edgesettings.get("Grooved", {})
        ).edgeObjects(self)
        # Mounting Edge
        edges.MountingSettings(
            self.thickness, True, **self.edgesettings.get("Mounting", {})
        ).edgeObjects(self)
        # Handle Edge
        edges.HandleEdgeSettings(
            self.thickness, True, **self.edgesettings.get("HandleEdge", {})
        ).edgeObjects(self)
        # HexHoles
        self.hexHolesSettings = HexHolesSettings(
            self.thickness, True, **self.edgesettings.get("HexHoles", {})
        )
        # Lids

        self.lidSettings = LidSettings(
            self.thickness, True, **self.edgesettings.get("Lid", {})
        )
        self.lid = Lid(self, self.lidSettings)

        # Nuts
        self.addPart(NutHole(self, None))
        # Gears
        self.addPart(gears.Gears(self))
        s = edges.GearSettings(
            self.thickness, True, **self.edgesettings.get("Gear", {})
        )
        self.addPart(edges.RackEdge(self, s))
        self.addPart(pulley.Pulley(self))
        self.addPart(parts.Parts(self))

    def adjustSize(
        self,
        square,
        e1: Union[bool, edges.BaseEdge] = True,
        e2: Union[bool, edges.BaseEdge] = True,
    ):
        # Char to edge object
        e1 = self.edges.get(e1, e1)
        e2 = self.edges.get(e2, e2)

        try:
            total = sum(square)
            walls = (len(square) - 1) * self.thickness
        except TypeError:
            total = square
            walls = 0

        for e in (e1, e2):
            if isinstance(e, edges.BaseEdge):
                walls += e.startwidth() + e.margin()
            elif e:
                walls += self.thickness

        try:
            if total > 0.0:
                factor = (total - walls) / total
            else:
                factor = 1.0
            return [s * factor for s in square]
        except TypeError:
            return square - walls

    def render(self):
        """Implement this method in your subclass.

        You will typically need to call .parseArgs() before calling this one
        """
        # Change settings and create new Edges and part classes here
        raise NotImplementedError

    def cc(
        self,
        callback,
        number: int,
        x: float = 0.0,
        y: Optional[float] = None,
        a: float = 0.0,
    ):
        """Call callback from edge of a part

        :param callback: callback (callable or list of callables)
        :param number: number of the callback
        :param x:  (Default value = 0.0) x position to be call on
        :param y:  (Default value = None) y position to be called on (default does burn correction)
        """
        if y is None:
            y = self.burn

        if hasattr(callback, "__getitem__"):
            try:
                callback = callback[number]
                number = None
            except (KeyError, IndexError):
                pass

        if callback and callable(callback):
            with self.saved_context():
                self.moveTo(x, y, a)
                if number is None:
                    callback()
                else:
                    callback(number)
            self.context.move_to(0, 0)

    def getEntry(self, param: Union[List, Any], idx: int):
        """
        Get entry from list or items itself

        :param param: list or item
        :param idx: index in list
        """
        if isinstance(param, list):
            if len(param) > idx:
                return param[idx]
            else:
                return None
        else:
            return param

    def close(self):
        """Finish rendering

        Flush canvas to disk and convert output to requested format if needed.
        Call after .render()"""
        if self.context is None:
            return

        self.context.stroke()
        self.context = None

        self.surface.set_metadata(self.metadata)

        self.surface.flush()
        self.surface.finish(self.inner_corners)

        self.formats.convert(self.output, self.format, self.metadata)
        if self.inkscapefile:
            try:
                out = sys.stdout.buffer
            except AttributeError:
                out = sys.stdout
            svgutil.svgMerge(self.output, self.inkscapefile, out)

    ############################################################
    ### Turtle graphics commands
    ############################################################

    def corner(
        self, degrees: Union[float, Tuple[float, float]], radius: float = 0, tabs=0
    ):
        """
        Draw a corner

        This is what does the burn corrections

        :param degrees: angle
        :param radius:  (Default value = 0)
        """

        try:
            degrees, radius = degrees
        except Exception:
            pass

        rad = degrees * math.pi / 180

        if tabs and self.tabs:
            if degrees > 0:
                r_ = radius + self.burn
                tabrad = self.tabs / max(r_, 0.01)
            else:
                r_ = radius - self.burn
                tabrad = -self.tabs / max(r_, 0.01)

            length = abs(r_ * rad)
            tabs = min(tabs, int(length // (tabs * 3 * self.tabs)))
        if tabs and self.tabs:
            square = (length - tabs * self.tabs) / tabs
            lang = math.degrees(square / r_)
            if degrees < 0:
                lang = -lang
            # print(degrees, radius, l, lang, tabs, math.degrees(tabrad))
            self.corner(lang / 2.0, radius)
            for i in range(tabs - 1):
                self.moveArc(math.degrees(tabrad), r_)
                self.corner(lang, radius)
            if tabs:
                self.moveArc(math.degrees(tabrad), r_)
            self.corner(lang / 2.0, radius)
            return

        if (radius > 0.5 * self.burn and abs(degrees) > 36) or (abs(degrees) > 100):
            steps = int(abs(degrees) / 36.0) + 1
            for _ in range(steps):
                self.corner(float(degrees) / steps, radius)
            return

        if degrees > 0:
            self.context.arc(
                0,
                radius + self.burn,
                radius + self.burn,
                -0.5 * math.pi,
                rad - 0.5 * math.pi,
            )
        elif radius > self.burn:
            self.context.arc_negative(
                0,
                -(radius - self.burn),
                radius - self.burn,
                0.5 * math.pi,
                rad + 0.5 * math.pi,
            )
        else:  # not rounded inner corner
            self.context.arc_negative(
                0,
                self.burn - radius,
                self.burn - radius,
                -0.5 * math.pi,
                -0.5 * math.pi + rad,
            )

        self._continueDirection(rad)

    def edge(self, length, tabs=0):
        """
        Simple line
        :param length: length in mm
        """
        self.context.move_to(0, 0)
        if tabs and self.tabs:
            if self.tabs > length:
                self.context.move_to(length, 0)
            else:
                tabs = min(tabs, max(1, int(length // (tabs * 3 * self.tabs))))
                square = (length - tabs * self.tabs) / tabs
                self.context.line_to(0.5 * square, 0)
                for i in range(tabs - 1):
                    self.context.move_to((i + 0.5) * square + self.tabs, 0)
                    self.context.line_to((i + 0.5) * square + self.tabs + square, 0)
                if tabs == 1:
                    self.context.move_to((tabs - 0.5) * square + self.tabs, 0)
                else:
                    self.context.move_to((tabs - 0.5) * square + 2 * self.tabs, 0)

                self.context.line_to(length, 0)
        else:
            self.context.line_to(length, 0)
        self.context.translate(*self.context.get_current_point())

    def step(self, out):
        """
        Create a parallel step perpendicular to the current direction
        Positive values move to the outside of the part
        """
        if out > 1e-5:
            self.corner(-90)
            self.edge(out)
            self.corner(90)
        elif out < -1e-5:
            self.corner(90)
            self.edge(-out)
            self.corner(-90)

    def curveTo(self, x1, y1, x2, y2, x3, y3):
        """control point 1, control point 2, end point

        :param x1:
        :param y1:
        :param x2:
        :param y2:
        :param x3:
        :param y3:
        """
        self.context.curve_to(x1, y1, x2, y2, x3, y3)
        dx = x3 - x2
        dy = y3 - y2
        rad = math.atan2(dy, dx)
        self._continueDirection(rad)

    def polyline(self, *args):
        """
        Draw multiple connected lines

        :param args: Alternating length in mm and angle in degrees.

        lengths may be a tuple (length, #tabs)
        angles may be tuple (angle, radius)
        """
        for i, arg in enumerate(args):
            if i % 2:
                if isinstance(arg, tuple):
                    self.corner(*arg)
                else:
                    self.corner(arg)
            else:
                if isinstance(arg, tuple):
                    self.edge(*arg)
                else:
                    self.edge(arg)

    def bedBoltHole(self, length, bedBoltSettings=None, tabs=0):
        """
        Draw an edge with slot for a bed bolt

        :param length: length of the edge in mm
        :param bedBoltSettings:  (Default value = None) Dimensions of the slot
        """
        d, d_nut, h_nut, square, l1 = bedBoltSettings or self.bedBoltSettings
        self.edge((length - d) / 2.0, tabs=tabs // 2)
        self.corner(90)
        self.edge(l1)
        self.corner(90)
        self.edge((d_nut - d) / 2.0)
        self.corner(-90)
        self.edge(h_nut)
        self.corner(-90)
        self.edge((d_nut - d) / 2.0)
        self.corner(90)
        self.edge(square - l1 - h_nut)
        self.corner(-90)
        self.edge(d)
        self.corner(-90)
        self.edge(square - l1 - h_nut)
        self.corner(90)
        self.edge((d_nut - d) / 2.0)
        self.corner(-90)
        self.edge(h_nut)
        self.corner(-90)
        self.edge((d_nut - d) / 2.0)
        self.corner(90)
        self.edge(l1)
        self.corner(90)
        self.edge((length - d) / 2.0, tabs=tabs - (tabs // 2))

    def edgeCorner(self, edge1, edge2, angle=90):
        """Make a corner between two Edges. Take width of edges into account"""
        edge1 = self.edges.get(edge1, edge1)
        edge2 = self.edges.get(edge2, edge2)

        self.edge(edge2.startwidth() * math.tan(math.radians(angle / 2.0)))
        self.corner(angle)
        self.edge(edge1.endwidth() * math.tan(math.radians(angle / 2.0)))

    def regularPolygon(self, corners=3, radius=None, h=None, side=None):
        """Give measures of a regular polygon

        :param corners: number of corners of the polygon
        :param radius: distance center to one of the corners
        :param h: distance center to one of the sides (height of sector)
        :param side: length of one side
        :return: (radius, h, side)
        """
        if radius:
            side = 2 * math.sin(math.radians(180.0 / corners)) * radius
            h = radius * math.cos(math.radians(180.0 / corners))
        elif h:
            side = 2 * math.tan(math.radians(180.0 / corners)) * h
            radius = ((side / 2.0) ** 2 + h**2) ** 0.5
        elif side:
            h = 0.5 * side * math.tan(math.radians(90 - 180.0 / corners))
            radius = ((side / 2.0) ** 2 + h**2) ** 0.5

        return radius, h, side

    @restore
    def regularPolygonAt(self, x, y, corners, angle=0, r=None, h=None, side=None):
        """Draw regular polygon"""
        self.moveTo(x, y, angle)
        r, h, side = self.regularPolygon(corners, r, h, side)
        self.moveTo(-side / 2.0, -h - self.burn)
        for i in range(corners):
            self.edge(side)
            self.corner(360.0 / corners)

    def regularPolygonWall(
        self,
        corners=3,
        r=None,
        h=None,
        side=None,
        edges="e",
        hole=None,
        callback=None,
        move=None,
    ):
        """Create regular polygon as a wall

        :param corners: number of corners of the polygon
        :param r: radius distance center to one of the corners
        :param h: distance center to one of the sides (height of sector)
        :param side: length of one side
        :param edges:  (Default value = "e", may be string/list of length corners)
        :param hole: diameter of central hole (Default value = 0)
        :param callback:  (Default value = None, middle=0, then sides=1..)
        :param move:  (Default value = None)
        """
        r, h, side = self.regularPolygon(corners, r, h, side)

        if not hasattr(edges, "__getitem__") or len(edges) == 1:
            edges = [edges] * corners
        edges = [self.edges.get(e, e) for e in edges]
        edges += edges  # append for wrapping around

        if corners % 2:
            th = (
                r
                + h
                + edges[0].spacing()
                + (
                    max(
                        edges[corners // 2].spacing(), edges[corners // 2 + 1].spacing()
                    )
                    / math.sin(math.radians(90 - 180 / corners))
                )
            )
        else:
            th = 2 * h + edges[0].spacing() + edges[corners // 2].spacing()

        tw = 0
        for i in range(corners):
            ang = (180 + 360 * i) / corners
            tw = max(
                tw,
                2
                * abs(
                    math.sin(math.radians(ang))
                    * (
                        r
                        + max(edges[i].spacing(), edges[i + 1].spacing())
                        / math.sin(math.radians(90 - 180 / corners))
                    )
                ),
            )

        if self.move(tw, th, move, before=True):
            return

        self.moveTo(0.5 * tw - 0.5 * side, edges[0].margin())

        if hole:
            self.hole(side / 2.0, h + edges[0].startwidth() + self.burn, hole / 2.0)
        self.cc(callback, 0, side / 2.0, h + edges[0].startwidth() + self.burn)
        for i in range(corners):
            self.cc(callback, i + 1, 0, edges[i].startwidth() + self.burn)
            edges[i](side)
            self.edgeCorner(edges[i], edges[i + 1], 360.0 / corners)

        self.move(tw, th, move)

    def grip(self, length, depth):
        """Corrugated edge useful as a gipping area

        :param length: length
        :param depth: depth of the grooves
        """
        grooves = max(int(length // (depth * 2.0)) + 1, 1)
        depth = length / grooves / 4.0
        for groove in range(grooves):
            self.corner(90, depth)
            self.corner(-180, depth)
            self.corner(90, depth)

    def _latchHole(self, length):
        """
        :param length:
        """
        self.edge(1.1 * self.thickness)
        self.corner(-90)
        self.edge(length / 2.0 + 0.2 * self.thickness)
        self.corner(-90)
        self.edge(1.1 * self.thickness)

    def _latchGrip(self, length):
        """
        :param length:
        """
        self.corner(90, self.thickness / 4.0)
        self.grip(
            length / 2.0 - self.thickness / 2.0 - 0.2 * self.thickness,
            self.thickness / 2.0,
        )
        self.corner(90, self.thickness / 4.0)

    def latch(self, length, positive=True, reverse=False):
        """Latch to fix a flex box door to the box

        :param length: length in mm
        :param positive:  (Default value = True) False: Door side; True: Box side
        :param reverse:  (Default value = False) True when running away from the latch
        """
        if positive:
            if reverse:
                self.edge(length / 2.0)
            self.corner(-90)
            self.edge(self.thickness)
            self.corner(90)
            self.edge(length / 2.0)
            self.corner(90)
            self.edge(self.thickness)
            self.corner(-90)
            if not reverse:
                self.edge(length / 2.0)
        else:
            if reverse:
                self._latchGrip(length)
            else:
                self.corner(90)
            self._latchHole(length)
            if not reverse:
                self._latchGrip(length)
            else:
                self.corner(90)

    def handle(self, x, h, hl, r=30):
        """Creates an Edge with a handle

        :param x: width in mm
        :param h: height in mm
        :param hl: height if th grip hole
        :param r:  (Default value = 30) radius of the corners
        """
        d = (x - hl - 2 * r) / 2.0

        # Hole
        with self.saved_context():
            self.moveTo(d + 2 * r, 0)
            self.edge(hl - 2 * r)
            self.corner(-90, r)
            self.edge(h - 3 * r)
            self.corner(-90, r)
            self.edge(hl - 2 * r)
            self.corner(-90, r)
            self.edge(h - 3 * r)
            self.corner(-90, r)

        self.moveTo(0, 0)

        self.curveTo(d, 0, d, 0, d, -h + r)
        self.curveTo(r, 0, r, 0, r, r)
        self.edge(hl)
        self.curveTo(r, 0, r, 0, r, r)
        self.curveTo(h - r, 0, h - r, 0, h - r, -d)

    ### Navigation

    def moveTo(self, x, y=0.0, degrees=0):
        """
        Move coordinate system to given point

        :param x:
        :param y:  (Default value = 0.0)
        :param degrees:  (Default value = 0)
        """
        self.context.move_to(0, 0)
        self.context.translate(x, y)
        self.context.rotate(degrees * math.pi / 180.0)
        self.context.move_to(0, 0)

    def moveArc(self, angle, r=0.0):
        """
        :param angle:
        :param r: (Default value = 0.0)
        """
        if r < 0:
            r = -r
            angle = -angle

        rad = math.radians(angle)
        if angle > 0:
            self.moveTo(r * math.sin(rad), r * (1 - math.cos(rad)), angle)
        else:
            self.moveTo(r * math.sin(-rad), -r * (1 - math.cos(rad)), angle)

    def _continueDirection(self, angle=0):
        """
        Set coordinate system to current position (end point)

        :param angle:  (Default value = 0) heading
        """
        self.context.translate(*self.context.get_current_point())
        self.context.rotate(angle)

    def move(self, x, y, where, before=False, label=""):
        """Intended to be used by parts
        where can be combinations of "up" or "down", "left" or "right", "only",
        "mirror" and "rotated"
        when "only" is included the move is only done when before is True
        "mirror" will flip the part along the y-axis
        "rotated" draws the parts rotated 90 counter clockwise
        The function returns whether actual drawing of the part
        should be omitted.

        :param x: width of part
        :param y: height of part
        :param where: which direction to move
        :param before:  (Default value = False) called before or after part being drawn
        """
        if not where:
            where = ""

        terms = where.split()
        dontdraw = before and "only" in terms

        x += self.spacing
        y += self.spacing

        if "rotated" in terms:
            x, y = y, x

        moves = {
            "up": (0, y, False),
            "down": (0, -y, True),
            "left": (-x, 0, True),
            "right": (x, 0, False),
            "only": (0, 0, None),
            "mirror": (0, 0, None),
            "rotated": (0, 0, None),
        }

        if not before:
            # restore position
            self.context.restore()
            if self.labels and label:
                self.text(
                    label,
                    x / 2,
                    y / 2,
                    align="middle center",
                    color=Color.ANNOTATIONS,
                    fontsize=4,
                )
            self.context.stroke()

        for term in terms:
            if term not in moves:
                raise ValueError("Unknown direction: '%s'" % term)
            mx, my, movebeforeprint = moves[term]
            if movebeforeprint and before:
                self.moveTo(mx, my)
            elif (not movebeforeprint and not before) or dontdraw:
                self.moveTo(mx, my)
        if not dontdraw:
            if before:
                # paint debug rectangle
                if self.debug:
                    with self.saved_context():
                        self.set_source_color(Color.ANNOTATIONS)
                        self.context.rectangle(0, 0, x, y)
                # save position
                self.context.save()
                if "rotated" in terms:
                    self.moveTo(x, 0, 90)
                    x, y = y, x  # change back for "mirror"
                if "mirror" in terms:
                    self.moveTo(x, 0)
                    self.context.scale(-1, 1)
                self.moveTo(self.spacing / 2.0, self.spacing / 2.0)
        self.context.new_part()

        return dontdraw

    @restore
    def circle(self, x, y, r):
        """
        Draw a round disc

        :param x: position
        :param y: position
        :param r: radius
        """
        r += self.burn
        self.moveTo(x + r, y)
        a = 0
        n = 10
        da = 2 * math.pi / n
        for i in range(n):
            self.context.arc(-r, 0, r, a, a + da)
            a += da
        self.context.stroke()

    @restore
    @holeCol
    def regularPolygonHole(
        self, x, y, r=0.0, d=0.0, n=6, a=0.0, tabs=0, corner_radius=0.0
    ):
        """
        Draw a hole in shape of an n-edged regular polygon

        :param x: position
        :param y: position
        :param r: radius
        :param n: number of edges
        :param a: rotation angle
        """

        if not r:
            r = d / 2.0

        if n == 0:
            self.hole(x, y, r=r, tabs=tabs)
            return

        if r < self.burn:
            r = self.burn + 1e-9
        r_ = r - self.burn

        if corner_radius < self.burn:
            corner_radius = self.burn
        cr_ = corner_radius - self.burn

        side_length = 2 * r_ * math.sin(math.pi / n)
        # the corner chord:
        s = math.sqrt(2 * math.pow(cr_, 2) * (1 - math.cos(2 * math.pi / n)))
        # the missing portion of the rounded corner:
        b = math.sin(math.pi / n) / math.sin(2 * math.pi / n) * s
        # the flat portion of the side:
        flat_side_length = side_length - 2 * b

        self.moveTo(x, y, a)
        self.moveTo(r_, 0, 90 + 180 / n)
        self.moveTo(b, 0, 0)
        for _ in range(n):
            self.edge(flat_side_length)
            self.corner(360 / n, cr_)

    @restore
    @holeCol
    def hole(self, x, y, r=0.0, d=0.0, tabs=0):
        """
        Draw a round hole

        :param x: position
        :param y: position
        :param r: radius
        """

        if not r:
            r = d / 2.0
        if r < self.burn:
            r = self.burn + 1e-9
        r_ = r - self.burn
        self.moveTo(x + r_, y, -90)
        self.corner(-360, r, tabs)

    @restore
    @holeCol
    def rectangularHole(self, x, y, dx, dy, r=0, center_x=True, center_y=True):
        """
        Draw a rectangular hole

        :param x: position
        :param y: position
        :param dx: width
        :param dy: height
        :param r:  (Default value = 0) radius of the corners
        :param center_x:  (Default value = True) if True, x position is the center, else the start
        :param center_y:  (Default value = True) if True, y position is the center, else the start
        """
        r = min(r, dx / 2.0, dy / 2.0)
        x_start = x if center_x else x + dx / 2.0
        y_start = y - dy / 2.0 if center_y else y
        self.moveTo(x_start, y_start + self.burn, 180)
        self.edge(
            dx / 2.0 - r
        )  # start with an edge to allow easier change of inner corners
        for d in (dy, dx, dy, dx / 2.0 + r):
            self.corner(-90, r)
            self.edge(d - 2 * r)

    @restore
    @holeCol
    def dHole(self, x, y, r=None, d=None, w=None, rel_w=0.75, angle=0):
        """
        Draw a hole for a shaft with flat edge - D shaped hole

        :param x: center position
        :param y: center position
        :param r: radius (overrides d)
        :param d: diameter
        :param w: width measured against flat side in mm
        :param rel_w: width in percent
        :param angle: orientation (rotation) of the flat side
        """

        if r is None:
            r = d / 2.0
        if w is None:
            w = 2.0 * r * rel_w
        w -= r
        if r <= 0.0:
            return
        if abs(w) > r:
            return self.hole(x, y, r)

        a = math.degrees(math.acos(w / r))
        self.moveTo(x, y, angle - a)
        self.moveTo(r - self.burn, 0, -90)
        self.corner(-360 + 2 * a, r)
        self.corner(-a)
        self.edge(2 * r * math.sin(math.radians(a)))

    @restore
    @holeCol
    def flatHole(self, x, y, r=None, d=None, w=None, rel_w=0.75, angle=0):
        """
        Draw a hole for a shaft with two opposed flat edges - ( ) shaped hole

        :param x: center position
        :param y: center position
        :param r: radius (overrides d)
        :param d: diameter
        :param w: width measured against flat side in mm
        :param rel_w: width in percent
        :param angle: orientation (rotation) of the flat sides
        """

        if r is None:
            r = d / 2.0
        if w is None:
            w = r * rel_w
        else:
            w = w / 2.0

        if r < 0.0:
            return
        if abs(w) > r:
            return self.hole(x, y, r)

        a = math.degrees(math.acos(w / r))
        self.moveTo(x, y, angle - a)
        self.moveTo(r - self.burn, 0, -90)
        for i in range(2):
            self.corner(-180 + 2 * a, r)
            self.corner(-a)
            self.edge(2 * r * math.sin(math.radians(a)))
            self.corner(-a)

    @restore
    @holeCol
    def mountingHole(self, x, y, d_shaft, d_head=0.0, angle=0, tabs=0):
        """
        Draw a pear shaped mounting hole for sliding over a screw head. Total height = 1.5* d_shaft + d_head

        :param x: position
        :param y: position
        :param d_shaft: diameter of the screw shaft
        :param d_head: diameter of the screw head
        :param angle: rotation angle of the hole
        """

        if d_shaft < (2 * self.burn):
            return  # no hole if diameter is smaller then the capabilities of the machine

        if not d_head or d_head < (2 * self.burn):  # if no head diameter is given
            self.hole(x, y, d=d_shaft, tabs=tabs)  # only a round hole is generated
            return

        rs = d_shaft / 2
        rh = d_head / 2

        self.moveTo(x, y, angle)
        self.moveTo(0, rs - self.burn, 0)
        self.corner(-180, rs, tabs)
        self.edge(2 * rs, tabs)
        a = math.degrees(math.asin(rs / rh))
        self.corner(90 - a, 0, tabs)
        self.corner(-360 + 2 * a, rh, tabs)
        self.corner(90 - a, 0, tabs)
        self.edge(2 * rs, tabs)

    @restore
    def text(
        self,
        text,
        x=0,
        y=0,
        angle=0,
        align="",
        fontsize=10,
        color=[0.0, 0.0, 0.0],
        font="Arial",
    ):
        """
        Draw text

        :param text: text to render
        :param x:  (Default value = 0)
        :param y:  (Default value = 0)
        :param angle:  (Default value = 0)
        :param align:  (Default value = "") string with combinations of (top|middle|bottom) and (left|center|right) separated by a space
        """
        self.moveTo(x, y, angle)
        text = text.split("\n")

        lines = len(text)
        height = lines * fontsize + (lines - 1) * 0.4 * fontsize
        align = align.split()
        halign = "left"
        moves = {
            "top": -height,
            "middle": -0.5 * height,
            "bottom": 0,
            "left": "left",
            "center": "middle",
            "right": "end",
        }
        for a in align:
            if a in moves:
                if isinstance(moves[a], str):
                    halign = moves[a]
                else:
                    self.moveTo(0, moves[a])
            else:
                raise ValueError("Unknown alignment: %s" % align)

        for line in reversed(text):
            self.context.show_text(
                line, fs=fontsize, align=halign, rgb=color, font=font
            )
            self.moveTo(0, 1.4 * fontsize)

    tx_sizes = {
        1: 0.61,
        2: 0.70,
        3: 0.82,
        4: 0.96,
        5: 1.06,
        6: 1.27,
        7: 1.49,
        8: 1.75,
        9: 1.87,
        10: 2.05,
        15: 2.40,
        20: 2.85,
        25: 3.25,
        30: 4.05,
        40: 4.85,
        45: 5.64,
        50: 6.45,
        55: 8.05,
        60: 9.60,
        70: 11.20,
        80: 12.80,
        90: 14.40,
        100: 16.00,
    }

    @restore
    @holeCol
    def TX(self, size, x=0, y=0, angle=0):
        """Draw a star pattern

        :param size: 1 to 100
        :param x: (Default value = 0)
        :param y: (Default value = 0)
        :param angle: (Default value = 0)
        """
        self.moveTo(x, y, angle)

        size = self.tx_sizes.get(size, 0)
        ri = 0.5 * size * math.tan(math.radians(30))
        ro = ri * (2**0.5 - 1)

        self.moveTo(size * 0.5 - self.burn, 0, -90)
        for i in range(6):
            self.corner(45, ri)
            self.corner(-150, ro)
            self.corner(45, ri)

    nema_sizes = {
        #    motor,flange, holes, screws
        8: (20.3, 16, 15.4, 3),
        11: (28.2, 22, 23, 4),
        14: (35.2, 22, 26, 4),
        16: (39.2, 22, 31, 4),
        17: (42.2, 22, 31, 4),
        23: (56.4, 38.1, 47.1, 5.2),
        24: (60, 36, 49.8, 5.1),
        34: (86.3, 73, 69.8, 6.6),
        42: (110, 55.5, 89, 8.5),
    }

    @restore
    def NEMA(self, size, x=0, y=0, angle=0, screwholes=None):
        """Draw holes for mounting a NEMA stepper motor

        :param size: Nominal size in tenths of inches
        :param x:  (Default value = 0)
        :param y:  (Default value = 0)
        :param angle:  (Default value = 0)
        :param screwholes:
        """
        width, flange, holedistance, diameter = self.nema_sizes[size]
        if screwholes:
            diameter = screwholes
        self.moveTo(x, y, angle)
        if self.debug:
            self.rectangularHole(0, 0, width, width)
        self.hole(0, 0, 0.5 * flange)
        for x in (-1, 1):
            for y in (-1, 1):
                self.hole(
                    x * 0.5 * holedistance, y * 0.5 * holedistance, 0.5 * diameter
                )

    def drawPoints(self, lines, kerfdir=1, close=True):
        if not lines:
            return

        if kerfdir != 0:
            lines = kerf(lines, self.burn * kerfdir, closed=close)

        self.context.save()
        self.context.move_to(*lines[0])

        for x, y in lines[1:]:
            self.context.line_to(x, y)

        if close:
            self.context.line_to(*lines[0])
        self.context.restore()

    def qrcode(self, content, box_size=1.0, color=Color.ETCHING, move=None):
        q = qrcode.QRCode(image_factory=BoxesQrCodeFactory, box_size=box_size * 10)
        q.add_data(content)
        m = q.get_matrix()
        tw, th = len(m) * box_size, len(m[0]) * box_size
        if self.move(tw, th, move, True):
            return

        self.set_source_color(color)
        q.make_image(context=self.context)

        self.move(tw, th, move)

    @restore
    def showBorderPoly(self, border, color=Color.ANNOTATIONS):
        """
        draw border polygon (for debugging only)

        :param border:     array with coordinate [(x0,y0), (x1,y1),...] of the border polygon
        :param color:
        """
        self.set_source_color(color)
        self.context.save()
        self.context.move_to(*border[0])

        for x, y in border[1:]:
            self.context.line_to(x, y)

        self.context.line_to(*border[0])
        self.context.restore()

        i = 0
        for x, y in border:
            i += 1
            self.hole(x, y, 0.5, color=color)
            self.text(str(i), x, y, fontsize=2, color=color)

    @restore
    @holeCol
    def fillHoles(
        self,
        pattern,
        border,
        max_radius,
        hspace=3,
        bspace=0,
        min_radius=0.5,
        style="round",
        bar_length=50,
        max_random=1000,
    ):
        """
        fill a polygon defined by its outline with holes

        :param pattern:     defines the hole pattern - currently "random", "hex", "square" "hbar" or "vbar" are supported
        :param border:      array with coordinate [(x0,y0), (x1,y1),...] of the border polygon
        :param max_radius:  maximum hole radius
        :param hspace:      space between holes
        :param bspace:      space to border
        :param min_radius:  minimum hole radius
        :param style:       defines hole style - currently one of "round", "triangle", "square", "hexagon" or "octagon"
        :param bar_length:  maximum bar length
        :param max_random:  maximum number of random holes
        """
        if pattern not in ["random", "hex", "square", "hbar", "vbar"]:
            return

        a = 0
        if style == "round":
            n = 0
        elif style == "triangle":
            n = 3
            a = 60
        elif style == "square":
            n = 4
        elif style == "hexagon":
            n = 6
            a = 30
        elif style == "octagon":
            n = 8
            a = 22.5
        else:
            raise ValueError("fillHoles - unknown hole style: %s)" % style)

        # note to myself: ^y  x>

        if self.debug:
            self.showBorderPoly(border)

        borderPoly = Polygon(border)
        min_x, min_y, max_x, max_y = borderPoly.bounds

        if pattern == "vbar":
            border = [(max_y - y + min_y, x) for x, y in border]
            borderPoly = Polygon(border)
            min_x, min_y, max_x, max_y = borderPoly.bounds
            self.moveTo(0, max_x + min_x, -90)
            pattern = "hbar"
            if self.debug:
                self.showBorderPoly(border, color=Color.MAGENTA)

        row = 0
        i = 0

        # calc the next smaller radius to fit an 'optimum' number of circles
        # for x direction
        nx = math.ceil(
            (max_x - min_x - 2 * bspace + hspace) / (2 * max_radius + hspace)
        )
        max_radius_x = (max_x - min_x - 2 * bspace - (nx - 1) * hspace) / nx / 2

        # for y direction
        if pattern == "hex":
            ny = math.ceil(
                (max_y - min_y - 2 * bspace - 2 * max_radius)
                / (math.sqrt(3) / 2 * (2 * max_radius + hspace))
            )
            max_radius_y = (
                max_y - min_y - 2 * bspace - math.sqrt(3) / 2 * ny * hspace
            ) / (math.sqrt(3) * ny + 2)
        else:
            ny = math.ceil(
                (max_y - min_y - 2 * bspace + hspace) / (2 * max_radius + hspace)
            )
            max_radius_y = (max_y - min_y - 2 * bspace - (ny - 1) * hspace) / ny / 2

        if pattern == "random":
            grid = {}
            misses = 0  # in a row
            while i < max_random and misses < 20:
                i += 1
                misses += 1
                # random new point
                x = random.randrange(
                    math.floor(min_x + bspace), math.ceil(max_x - bspace)
                )  # randomness takes longer to compute
                y = random.randrange(
                    math.floor(min_y + bspace), math.ceil(max_y - bspace)
                )  # but generates a new pattern for each run
                pt = Point(x, y).buffer(min_radius + bspace)
                # check if point is within border
                if borderPoly.contains(pt):
                    pt1 = Point(x, y)
                    grid_x = int(x // (2 * max_radius + hspace))
                    grid_y = int(y // (2 * max_radius + hspace))
                    # compute distance between hole and border
                    bdist = borderPoly.exterior.distance(pt1) - bspace
                    # compute minimum distance to all other holes
                    hdist = max_radius
                    try:  # learned from https://medium.com/techtofreedom/5-ways-to-break-out-of-nested-loops-in-python-4c505d34ace7
                        for gx in (-1, 0, 1):
                            for gy in (-1, 0, 1):
                                for pt2 in grid.get((grid_x + gx, grid_y + gy), []):
                                    pt3 = Point(pt2.x, pt2.y)
                                    hdist = min(
                                        hdist, pt1.distance(pt3) - pt2.z - hspace
                                    )
                                    if hdist < min_radius:
                                        hdist = 0
                                        raise StopIteration
                    except StopIteration:
                        pass
                    # find maximum radius depending on distances
                    r = min(bdist, hdist)
                    # if too small, dismiss cycle
                    if r < min_radius:
                        continue
                    # if too large, limit to max size
                    if r > max_radius:
                        r = max_radius
                    # store in grid with radius as z value
                    grid.setdefault((grid_x, grid_y), []).append(Point(x, y, r))
                    misses = 0
                    # and finally paint the hole
                    self.regularPolygonHole(x, y, r=r, n=n, a=a)
                    # rinse and repeat

        elif pattern in ("square", "hex"):
            # use 'optimum' hole size
            max_radius = min(max_radius_x, max_radius_y)

            # check if at least one line fits (we do horizontal filling)
            if (max_y - min_y) < (2 * max_radius + 2 * bspace):
                return

            # make cutPolys a little wider to avoid
            # overlapping with lines to be cut
            outerCutPoly = borderPoly.buffer(-1 * (bspace - 0.000001), join_style=2)
            outerTestPoly = borderPoly.buffer(-1 * (bspace - 0.01), join_style=2)
            # shrink original polygon to get place for full size polygons
            innerCutPoly = borderPoly.buffer(
                -1 * (bspace + max_radius - 0.0001), join_style=2
            )
            innerTestPoly = borderPoly.buffer(
                -1 * (bspace + max_radius - 0.001), join_style=2
            )

            # get left and right boundaries of cut polygon
            x_cpl, y_cpl, x_cpr, y_cpr = outerCutPoly.bounds

            if self.debug:
                self.showBorderPoly(list(outerCutPoly.exterior.coords))
                self.showBorderPoly(list(innerCutPoly.exterior.coords))

            # set startpoint
            y = min_y + bspace + max_radius_y

            while y < (max_y - bspace - max_radius_y):
                if pattern == "square" or row % 2 == 0:
                    xs = min_x + bspace + max_radius_x
                else:
                    xs = min_x + max_radius_x * 2 + hspace / 2 + bspace

                # create line segments cut by the polygons
                line_complete = LineString([(x_cpl, y), (max_x + 1, y)])
                # cut accurate
                outer_line_split = split(line_complete, outerCutPoly)
                line_complete = LineString([(x_cpl, y), (max_x + 1, y)])
                inner_line_split = split(line_complete, innerCutPoly)
                inner_line_index = 0

                if self.debug and False:
                    for line in inner_line_split.geoms:
                        self.hole(line.bounds[0], line.bounds[1], 1.1)
                        self.hole(line.bounds[2], line.bounds[3], 0.9)

                # process each line
                for line_this in outer_line_split.geoms:
                    if self.debug and False:  # enable to debug missing lines
                        x_start, y_start, x_end, y_end = line_this.bounds
                        with self.saved_context():
                            self.moveTo(x_start, y_start, 0)
                            self.hole(0, 0, 0.5)
                            self.edge(x_end - x_start)
                        with self.saved_context():
                            self.moveTo(x_start, y_start, 0)
                            self.text(
                                str(outerTestPoly.contains(line_this)),
                                0,
                                0,
                                fontsize=2,
                                color=Color.ANNOTATIONS,
                            )
                        with self.saved_context():
                            self.moveTo(x_end, y_end, 0)
                            self.hole(0, 0, 0.5)

                    if not outerTestPoly.contains(line_this):
                        continue
                    x_start, y_start, x_end, y_end = line_this.bounds
                    # initialize walking x coordinate
                    xw = (
                        math.ceil((x_start - xs) / (2 * max_radius_x + hspace))
                        * (2 * max_radius_x + hspace)
                    ) + xs

                    # look up matching inner line
                    while inner_line_index < len(inner_line_split) and (
                        inner_line_split.geoms[inner_line_index].bounds[2] < xw
                        or not innerTestPoly.contains(
                            inner_line_split.geoms[inner_line_index]
                        )
                    ):
                        inner_line_index += 1

                    # and process line
                    while not xw > x_end:
                        # are we in inner polygon already?
                        if (
                            len(inner_line_split) > inner_line_index
                            and xw > inner_line_split.geoms[inner_line_index].bounds[0]
                        ):
                            # place inner, full size polygons
                            while (
                                xw < inner_line_split.geoms[inner_line_index].bounds[2]
                            ):
                                self.regularPolygonHole(xw, y, r=max_radius, n=n, a=a)
                                xw += 2 * max_radius_x + hspace
                            # forward to next inner line
                            while inner_line_index < len(inner_line_split) and (
                                inner_line_split.geoms[inner_line_index].bounds[0] < xw
                                or not innerTestPoly.contains(
                                    inner_line_split.geoms[inner_line_index]
                                )
                            ):
                                inner_line_index += 1
                            if xw > x_end:
                                break

                        # Check distance to border to size the polygon
                        pt = Point(xw, y)
                        r = min(borderPoly.exterior.distance(pt) - bspace, max_radius)
                        # if too small, dismiss
                        if r >= min_radius:
                            self.regularPolygonHole(xw, y, r=r, n=n, a=a)
                        xw += 2 * max_radius_x + hspace

                row += 1
                if pattern == "square":
                    y += 2 * max_radius_y + hspace - 0.0001
                else:
                    y += (math.sqrt(3) / 2 * (2 * max_radius_y + hspace)) - 0.0001

        elif pattern == "hbar":
            # 'optimum' hole size to be used
            max_radius = max_radius_y
            # check if at least one bar fits
            if (max_y - min_y) < (2 * max_radius + 2 * bspace):
                return

            # shrink original polygon
            shrinkPoly = borderPoly.buffer(
                -1 * (bspace + max_radius - 0.01), join_style=2
            )
            cutPoly = borderPoly.buffer(
                -1 * (bspace + max_radius - 0.000001), join_style=2
            )

            if self.debug:
                self.showBorderPoly(list(shrinkPoly.exterior.coords))

            segment_length = [bar_length / 2, bar_length]
            segment_max = 1
            segment_toggle = False

            # set startpoint
            y = min_y + bspace + max_radius
            # and calc step width
            step_y = 2 * max_radius_y + hspace - 0.0001

            while y < (max_y - bspace - max_radius):
                # toggle segment length each new line
                if segment_toggle:
                    segment_max = 0
                segment_toggle ^= 1

                # create line from left to right and cut according to shrunk polygon
                line_complete = LineString([(min_x - 1, y), (max_x + 1, y)])
                line_split = split(line_complete, cutPoly)

                # process each line
                for line_this in line_split.geoms:
                    if self.debug and False:  # enable to debug missing lines
                        x_start, y_start, x_end, y_end = line_this.bounds
                        with self.saved_context():
                            self.moveTo(x_start, y_start, 0)
                            self.hole(0, 0, 0.5)
                            self.edge(x_end - x_start)
                        with self.saved_context():
                            self.moveTo(x_start, y_start, 0)
                            self.text(
                                str(shrinkPoly.contains(line_this)),
                                0,
                                0,
                                fontsize=2,
                                color=Color.ANNOTATIONS,
                            )
                        with self.saved_context():
                            self.moveTo(x_end, y_end, 0)
                            self.hole(0, 0, 0.5)

                    if shrinkPoly.contains(line_this):
                        # long segment are cut down further
                        if line_this.length > segment_length[segment_max]:
                            line_working = line_this
                            length = line_working.length
                            while length > 0:
                                x_start, y_start, xw_end, yw_end = line_working.bounds
                                # calculate point with required distance from start point
                                p = line_working.interpolate(
                                    segment_length[segment_max]
                                )
                                # and use its coordinates as endpoint for this segment
                                x_end = p.x
                                y_end = p.y
                                # draw segment
                                self.set_source_color(Color.INNER_CUT)
                                with self.saved_context():
                                    self.moveTo(x_start, y_start + max_radius, 0)
                                    self.edge(x_end - x_start)
                                    self.corner(-180, max_radius)
                                    self.edge(x_end - x_start)
                                    self.corner(-180, max_radius)

                                if (
                                    self.debug and False
                                ):  # enable to debug cutting lines
                                    self.set_source_color(Color.ANNOTATIONS)
                                    with self.saved_context():
                                        self.moveTo(x_start, y_start, 0)
                                        self.edge(x_end - x_start)

                                    s = (
                                        "long - y: "
                                        + str(round(y, 1))
                                        + " xs: "
                                        + str(round(x_start, 1))
                                        + " xe: "
                                        + str(round(x_end, 1))
                                        + " l: "
                                        + str(round(length, 1))
                                        + " max: "
                                        + str(round(segment_length[segment_max], 1))
                                    )
                                    with self.saved_context():
                                        self.text(
                                            s,
                                            x_start,
                                            y_start,
                                            fontsize=2,
                                            color=Color.ANNOTATIONS,
                                        )

                                # subtract length of segmant from total segment length
                                length -= x_end - x_start + hspace + 2 * max_radius
                                # create remaining line to work with
                                line_working = LineString(
                                    [
                                        (x_end + hspace + 2 * max_radius, y_end),
                                        (xw_end, yw_end),
                                    ]
                                )
                                # next segment shall be long
                                segment_max = 1
                        else:
                            # short segment can be drawn instantly
                            x_start, y_start, x_end, y_end = line_this.bounds
                            self.set_source_color(Color.INNER_CUT)
                            with self.saved_context():
                                self.moveTo(x_start, y_start + max_radius, 0)
                                self.edge(x_end - x_start)
                                self.corner(-180, max_radius)
                                self.edge(x_end - x_start)
                                self.corner(-180, max_radius)

                            segment_max = 1
                            # short segment shall be skipped if a short segment shall start the line
                            if segment_toggle:
                                segment_max = 0
                y += step_y
        else:
            raise ValueError("fillHoles - unknown hole pattern: %s)" % pattern)

    def hexHolesRectangle(self, x, y, settings=None, skip=None):
        """Fills a rectangle with holes in a hex pattern.

        Settings have:
        r : radius of holes
        b : space between holes
        style : what types of holes (not yet implemented)

        :param x: width
        :param y: height
        :param settings:  (Default value = None)
        :param skip:  (Default value = None) function to check if hole should be present
               gets x, y, r, b, posx, posy
        """

        if settings is None:
            settings = self.hexHolesSettings
        r, b = settings.diameter / 2, settings.distance

        w = r + b / 2.0
        dist = w * math.cos(math.pi / 6.0)

        # how many half circles do fit
        cx = int((x - 2 * r) // (w)) + 2
        cy = int((y - 2 * r) // (dist)) + 2

        # what's left on the sides
        lx = (x - (2 * r + (cx - 2) * w)) / 2.0
        ly = (y - (2 * r + ((cy // 2) * 2) * dist - 2 * dist)) / 2.0

        for i in range(cy // 2):
            for j in range((cx - (i % 2)) // 2):
                px = 2 * j * w + r + lx
                py = i * 2 * dist + r + ly
                if i % 2:
                    px += w
                if skip and skip(x, y, r, b, px, py):
                    continue
                self.hole(px, py, r=r)

    def __skipcircle(self, x, y, r, b, posx, posy):
        cx, cy = x / 2.0, y / 2.0
        return dist(posx - cx, posy - cy) > (cx - r)

    def hexHolesCircle(self, d, settings=None):
        """
        Fill circle with holes in a hex pattern

        :param d: diameter of the circle
        :param settings:  (Default value = None)
        """
        self.hexHolesRectangle(d, d, settings=settings, skip=self.__skipcircle)

    def hexHolesPlate(self, x, y, rc, settings=None):
        """
        Fill a plate with holes in a hex pattern

        :param x: width
        :param y: height
        :param rc: radius of the corners
        :param settings:  (Default value = None)
        """

        def skip(x, y, r, b, posx, posy):
            """
            :param x:
            :param y:
            :param r:
            :param b:
            :param posx:
            :param posy:
            """
            posx = abs(posx - (x / 2.0))
            posy = abs(posy - (y / 2.0))

            wx = 0.5 * x - rc - r
            wy = 0.5 * y - rc - r

            if (posx <= wx) or (posy <= wx):
                return 0
            return dist(posx - wx, posy - wy) > rc

        self.hexHolesRectangle(x, y, settings, skip=skip)

    def hexHolesHex(self, h, settings=None, grow=None):
        """
        Fill a hexagon with holes in a hex pattern

        :param h: height
        :param settings:  (Default value = None)
        :param grow:  (Default value = None)
        """
        if settings is None:
            settings = self.hexHolesSettings
        r, b = settings.diameter / 2, settings.distance

        self.context.rectangle(0, 0, h, h)
        w = r + b / 2.0
        dist = w * math.cos(math.pi / 6.0)
        cy = 2 * int((h - 4 * dist) // (4 * w)) + 1

        leftover = h - 2 * r - (cy - 1) * 2 * r
        if grow == "space ":
            b += leftover / (cy - 1) / 2

        # recalculate with adjusted values
        w = r + b / 2.0
        dist = w * math.cos(math.pi / 6.0)

        self.moveTo(h / 2.0 - (cy // 2) * 2 * w, h / 2.0)
        for j in range(cy):
            self.hole(2 * j * w, 0, r)
        for i in range(1, cy / 2 + 1):
            for j in range(cy - i):
                self.hole(j * 2 * w + i * w, i * 2 * dist, r)
                self.hole(j * 2 * w + i * w, -i * 2 * dist, r)

    def flex2D(self, x, y, width=1):
        """
        Fill a rectangle with a pattern allowing bending in both axis

        :param x: width
        :param y: height
        :param width: width between the lines of the pattern in multiples of thickness
        """
        width *= self.thickness
        cx = int(x // (5 * width))
        cy = int(y // (5 * width))

        if cx == 0 or cy == 0:
            return

        wx = x / 5.0 / cx
        wy = y / 5.0 / cy

        armx = (4 * wx, 90, 4 * wy, 90, 2 * wx, 90, 2 * wy)
        army = (4 * wy, 90, 4 * wx, 90, 2 * wy, 90, 2 * wx)
        for i in range(cx):
            for j in range(cy):
                if (i + j) % 2:
                    with self.saved_context():
                        self.moveTo((5 * i) * wx, (5 * j) * wy)
                        self.polyline(*armx)
                    with self.saved_context():
                        self.moveTo((5 * i + 5) * wx, (5 * j + 5) * wy, -180)
                        self.polyline(*armx)
                else:
                    with self.saved_context():
                        self.moveTo((5 * i + 5) * wx, (5 * j) * wy, 90)
                        self.polyline(*army)
                    with self.saved_context():
                        self.moveTo((5 * i) * wx, (5 * j + 5) * wy, -90)
                        self.polyline(*army)
        self.context.stroke()

    @restore
    def fingerHoleRectangle(self, dx, dy, x=0.0, y=0.0, angle=0.0, outside=False):
        """
        Place finger holes for four walls - attaching a box on this plane

        :param dx: size in x direction
        :param dy: size in y direction
        :param x: x position of the center
        :param y: y position of the center
        :param angle: angle in which the rectangle is placed
        :param outside: measure size from the outside of the walls - not the inside
        """
        self.moveTo(x, y, angle)
        d = 0.5 * self.thickness
        if outside:
            d = -d

        self.fingerHolesAt(dx / 2 + d, -dy / 2, dy, 90)
        self.fingerHolesAt(-dx / 2 - d, -dy / 2, dy, 90)
        self.fingerHolesAt(-dx / 2, -dy / 2 - d, dx, 0)
        self.fingerHolesAt(-dx / 2, dy / 2 + d, dx, 0)

    ##################################################
    ### parts
    ##################################################

    def _splitWall(self, pieces, side):
        """helper for roundedPlate and surroundingWall
        figures out what sides to split
        """
        return [
            (False, False, False, False, True),
            (True, False, False, False, True),
            (True, False, True, False, True),
            (True, True, True, False, True),
            (True, True, True, True, True),
        ][pieces][side]

    def roundedPlate(
        self,
        x,
        y,
        r,
        edge="f",
        callback=None,
        holesMargin=None,
        holesSettings=None,
        bedBolts=None,
        bedBoltSettings=None,
        wallpieces=1,
        extend_corners=True,
        move=None,
    ):
        """Plate with rounded corner fitting to .surroundingWall()

        For the callbacks the sides are counted depending on wallpieces

        :param x: width
        :param y: height
        :param r: radius of the corners
        :param edge:
        :param callback:  (Default value = None)
        :param holesMargin:  (Default value = None) set to get hex holes
        :param holesSettings:  (Default value = None)
        :param bedBolts:  (Default value = None)
        :param bedBoltSettings:  (Default value = None)
        :param wallpieces: (Default value = 1) # of separate surrounding walls
        :param extend_corners: (Default value = True) have corners outset with the edges
        :param move:  (Default value = None)
        """
        corner_holes = True

        t = self.thickness
        edge = self.edges.get(edge, edge)
        overallwidth = x + 2 * edge.spacing()
        overallheight = y + 2 * edge.spacing()

        if self.move(overallwidth, overallheight, move, before=True):
            return

        lx = x - 2 * r
        ly = y - 2 * r

        self.moveTo(edge.spacing(), edge.margin())
        self.moveTo(r, 0)

        if wallpieces > 4:
            wallpieces = 4

        wallcount = 0
        for nr, square in enumerate((lx, ly, lx, ly)):
            if self._splitWall(wallpieces, nr):
                for i in range(2):
                    self.cc(callback, wallcount, y=edge.startwidth() + self.burn)
                    edge(
                        square / 2.0,
                        bedBolts=self.getEntry(bedBolts, wallcount),
                        bedBoltSettings=self.getEntry(bedBoltSettings, wallcount),
                    )
                    wallcount += 1
            else:
                self.cc(callback, wallcount, y=edge.startwidth() + self.burn)
                edge(
                    square,
                    bedBolts=self.getEntry(bedBolts, wallcount),
                    bedBoltSettings=self.getEntry(bedBoltSettings, wallcount),
                )
                wallcount += 1
            if extend_corners:
                if corner_holes:
                    with self.saved_context():
                        self.moveTo(0, edge.startwidth())
                        self.polyline(
                            0,
                            (90, r),
                            0,
                            -90,
                            t,
                            -90,
                            0,
                            (-90, r + t),
                            0,
                            -90,
                            t,
                            -90,
                            0,
                        )
                        self.context.stroke()
                self.corner(90, r + edge.startwidth())
            else:
                self.step(-edge.endwidth())
                self.corner(90, r)
                self.step(edge.startwidth())

        self.context.restore()
        self.context.save()

        self.moveTo(edge.margin(), edge.margin())

        if holesMargin is not None:
            self.moveTo(holesMargin, holesMargin)
            if r > holesMargin:
                r -= holesMargin
            else:
                r = 0
            self.hexHolesPlate(
                x - 2 * holesMargin, y - 2 * holesMargin, r, settings=holesSettings
            )

        self.move(overallwidth, overallheight, move)

    def surroundingWallPiece(self, cbnr, x, y, r, pieces=1):
        """
        Return the geometry of a pices of surroundingWall with the given
        callback number.
        :param cbnr: number of the callback corresponding to this part of the wall
        :param x: width of matching roundedPlate
        :param y: height of matching roundedPlate
        :param r: corner radius of matching roundedPlate
        :param pieces: (Default value = 1) number of separate pieces
        :return: (left, length, right) left and right are Booleans that are True if the start or end of the wall is on that side.
        """
        if pieces <= 2 and (y - 2 * r) < 1e-3:
            # remove zero length y sides
            sides = (x / 2 - r, x - 2 * r, x - 2 * r)
            if pieces > 0:  # hack to get the right splits
                pieces += 1
        else:
            sides = (x / 2 - r, y - 2 * r, x - 2 * r, y - 2 * r, x - 2 * r)

        wallcount = 0
        for nr, square in enumerate(sides):
            if self._splitWall(pieces, nr) and nr > 0:
                if wallcount == cbnr:
                    return (False, square / 2, True)
                wallcount += 1
                if wallcount == cbnr:
                    return (True, square / 2, False)
                wallcount += 1
            else:
                if wallcount == cbnr:
                    return (False, square, False)
                wallcount += 1
        return (False, 0.0, False)

    def surroundingWall(
        self,
        x,
        y,
        r,
        h,
        bottom="e",
        top="e",
        left="D",
        right="d",
        pieces=1,
        extend_corners=True,
        callback=None,
        move=None,
    ):
        """
        Wall(s) with flex filing around a roundedPlate()

        For the callbacks the sides are counted depending on pieces

        :param x: width of matching roundedPlate
        :param y: height of matching roundedPlate
        :param r: corner radius of matching roundedPlate
        :param h: inner height of the wall (without edges)
        :param bottom:  (Default value = 'e') Edge type
        :param top:  (Default value = 'e') Edge type
        :param left: (Default value = 'D') left edge(s)
        :param right: (Default value = 'd') right edge(s)
        :param pieces: (Default value = 1) number of separate pieces
        :param callback:  (Default value = None)
        :param move:  (Default value = None)
        """
        t = self.thickness
        c4 = (r + self.burn) * math.pi * 0.5  # circumference of quarter circle
        c4 = c4 / self.edges["X"].settings.stretch

        top = self.edges.get(top, top)
        bottom = self.edges.get(bottom, bottom)
        left = self.edges.get(left, left)
        right = self.edges.get(right, right)

        # XXX assumes startwidth == endwidth
        if extend_corners:
            topwidth = t
            bottomwidth = t
        else:
            topwidth = top.startwidth()
            bottomwidth = bottom.startwidth()

        overallwidth = (
            2 * x
            + 2 * y
            - 8 * r
            + 4 * c4
            + (self.edges["d"].spacing() + self.edges["D"].spacing() + self.spacing)
            * pieces
        )
        overallheight = h + max(t, top.spacing()) + max(t, bottom.spacing())

        if self.move(overallwidth, overallheight, move, before=True):
            return

        self.moveTo(left.spacing(), bottom.margin())

        wallcount = 0
        tops = []  # edges needed on the top for this wall segment

        if pieces <= 2 and (y - 2 * r) < 1e-3:
            # remove zero length y sides
            c4 *= 2
            sides = (x / 2 - r, x - 2 * r, x - 2 * r)
            if pieces > 0:  # hack to get the right splits
                pieces += 1
        else:
            sides = (x / 2 - r, y - 2 * r, x - 2 * r, y - 2 * r, x - 2 * r)

        for nr, square in enumerate(sides):
            if self._splitWall(pieces, nr) and nr > 0:
                self.cc(callback, wallcount, y=bottomwidth + self.burn)
                wallcount += 1
                bottom(square / 2.0)
                tops.append(square / 2.0)

                # complete wall segment
                with self.saved_context():
                    self.edgeCorner(bottom, right, 90)
                    right(h)
                    self.edgeCorner(right, top, 90)
                    for n, d in enumerate(reversed(tops)):
                        if n % 2:  # flex
                            self.step(topwidth - top.endwidth())
                            self.edge(d)
                            self.step(top.startwidth() - topwidth)
                        else:
                            top(d)
                    self.edgeCorner(top, left, 90)
                    left(h)
                    self.edgeCorner(left, bottom, 90)

                if nr == len(sides) - 1:
                    break
                # start new wall segment
                tops = []
                self.moveTo(right.margin() + left.margin() + self.spacing)
                self.cc(callback, wallcount, y=bottomwidth + self.burn)
                wallcount += 1
                bottom(square / 2.0)
                tops.append(square / 2.0)
            else:
                self.cc(callback, wallcount, y=bottomwidth + self.burn)
                wallcount += 1
                bottom(square)
                tops.append(square)
            self.step(bottomwidth - bottom.endwidth())
            self.edges["X"](c4, h + topwidth + bottomwidth)
            self.step(bottom.startwidth() - bottomwidth)
            tops.append(c4)

        self.move(overallwidth, overallheight, move)

    def rectangularWall(
        self,
        x,
        y,
        edges="eeee",
        ignore_widths=[],
        holesMargin=None,
        holesSettings=None,
        bedBolts=None,
        bedBoltSettings=None,
        callback=None,
        move=None,
        label="",
    ):
        """
        Rectangular wall for all kind of box like objects

        :param x: width
        :param y: height
        :param edges:  (Default value = "eeee") bottom, right, top, left
        :param ignore_widths: list of edge_widths added to adjacent edge
        :param holesMargin:  (Default value = None)
        :param holesSettings:  (Default value = None)
        :param bedBolts:  (Default value = None)
        :param bedBoltSettings:  (Default value = None)
        :param callback:  (Default value = None)
        :param move:  (Default value = None)
        :param label: rendered to identify parts, it is not meant to be cut or etched (Default value = "")
        """
        if len(edges) != 4:
            raise ValueError("four edges required")
        edges = [self.edges.get(e, e) for e in edges]
        edges += edges  # append for wrapping around
        overallwidth = x + edges[-1].spacing() + edges[1].spacing()
        overallheight = y + edges[0].spacing() + edges[2].spacing()

        if self.move(overallwidth, overallheight, move, before=True):
            return

        if 7 not in ignore_widths:
            self.moveTo(edges[-1].spacing())
        self.moveTo(0, edges[0].margin())
        for i, square in enumerate((x, y, x, y)):
            self.cc(callback, i, y=edges[i].startwidth() + self.burn)
            e1, e2 = edges[i], edges[i + 1]
            if 2 * i - 1 in ignore_widths or 2 * i - 1 + 8 in ignore_widths:
                square += edges[i - 1].endwidth()
            if 2 * i in ignore_widths:
                square += edges[i + 1].startwidth()
                e2 = self.edges["e"]
            if 2 * i + 1 in ignore_widths:
                e1 = self.edges["e"]

            edges[i](
                square,
                bedBolts=self.getEntry(bedBolts, i),
                bedBoltSettings=self.getEntry(bedBoltSettings, i),
            )
            self.edgeCorner(e1, e2, 90)

        if holesMargin is not None:
            self.moveTo(holesMargin, holesMargin + edges[0].startwidth())
            self.hexHolesRectangle(
                x - 2 * holesMargin, y - 2 * holesMargin, settings=holesSettings
            )

        self.move(overallwidth, overallheight, move, label=label)

    def flangedWall(
        self,
        x,
        y,
        edges="FFFF",
        flanges=None,
        r=0.0,
        callback=None,
        move=None,
        label="",
    ):
        """Rectangular wall with flanges extending the regular size

        This is similar to the rectangularWall but it may extend to either
        side. Sides with flanges may only have e, E, or F edges - the later
        being replaced with fingerHoles.

        :param x: width
        :param y: height
        :param edges:  (Default value = "FFFF") bottom, right, top, left
        :param flanges: (Default value = None) list of width of the flanges
        :param r: radius of the corners of the flange
        :param callback:  (Default value = None)
        :param move:  (Default value = None)
        :param label: rendered to identify parts, it is not meant to be cut or etched (Default value = "")
        """

        t = self.thickness

        if not flanges:
            flanges = [0.0] * 4

        while len(flanges) < 4:
            flanges.append(0.0)

        edges = [self.edges.get(e, e) for e in edges]
        # double to allow looping around
        edges = edges + edges
        flanges = flanges + flanges

        tw = x + edges[1].spacing() + flanges[1] + edges[3].spacing() + flanges[3]
        th = y + edges[0].spacing() + flanges[0] + edges[2].spacing() + flanges[2]

        if self.move(tw, th, move, True):
            return

        rl = min(r, max(flanges[-1], flanges[0]))
        self.moveTo(rl + edges[-1].margin(), edges[0].margin())

        for i in range(4):
            square = y if i % 2 else x

            rl = min(r, max(flanges[i - 1], flanges[i]))
            rr = min(r, max(flanges[i], flanges[i + 1]))
            self.cc(callback, i, x=-rl)
            if flanges[i]:
                if edges[i] is self.edges["F"] or edges[i] is self.edges["h"]:
                    self.fingerHolesAt(
                        flanges[i - 1] + edges[i - 1].endwidth() - rl,
                        0.5 * t + flanges[i],
                        square,
                        angle=0,
                    )
                self.edge(
                    square
                    + flanges[i - 1]
                    + flanges[i + 1]
                    + edges[i - 1].endwidth()
                    + edges[i + 1].startwidth()
                    - rl
                    - rr
                )
            else:
                self.edge(flanges[i - 1] + edges[i - 1].endwidth() - rl)
                edges[i](square)
                self.edge(flanges[i + 1] + edges[i + 1].startwidth() - rr)
            self.corner(90, rr)
        self.move(tw, th, move, label=label)

    def rectangularTriangle(
        self,
        x,
        y,
        edges="eee",
        r=0.0,
        num=1,
        bedBolts=None,
        bedBoltSettings=None,
        callback=None,
        move=None,
        label="",
    ):
        """
        Rectangular triangular wall

        :param x: width
        :param y: height
        :param edges:  (Default value = "eee") bottom, right[, diagonal]
        :param r: radius towards the hypotenuse
        :param num: (Default value = 1) number of triangles
        :param bedBolts:  (Default value = None)
        :param bedBoltSettings:  (Default value = None)
        :param callback:  (Default value = None)
        :param move:  (Default value = None)
        :param label: rendered to identify parts, it is not meant to be cut or etched (Default value = "")
        """
        edges = [self.edges.get(e, e) for e in edges]
        if len(edges) == 2:
            edges.append(self.edges["e"])
        if len(edges) != 3:
            raise ValueError("two or three edges required")

        r = min(r, x, y)
        a = math.atan2(y - r, float(x - r))
        alpha = math.degrees(a)
        if a > 0:
            width = (
                x
                + (edges[-1].spacing() + self.spacing) / math.sin(a)
                + edges[1].spacing()
                + self.spacing
            )
        else:
            width = (
                x
                + (edges[-1].spacing() + self.spacing)
                + edges[1].spacing()
                + self.spacing
            )
        height = (
            y
            + edges[0].spacing()
            + edges[2].spacing() * math.cos(a)
            + 2 * self.spacing
            + self.spacing
        )
        if num > 1:
            width = 2 * width - x + r - self.spacing
        dx = width - x - edges[1].spacing() - self.spacing / 2
        dy = edges[0].margin() + self.spacing / 2

        overallwidth = width * (num // 2 + num % 2) - self.spacing
        overallheight = height - self.spacing

        if self.move(overallwidth, overallheight, move, before=True):
            return

        if self.debug:
            self.rectangularHole(width / 2.0, height / 2.0, width, height)

        self.moveTo(dx - self.spacing / 2, dy - self.spacing / 2)

        for n in range(num):
            for i, square in enumerate((x, y)):
                self.cc(callback, i, y=edges[i].startwidth() + self.burn)
                edges[i](
                    square,
                    bedBolts=self.getEntry(bedBolts, i),
                    bedBoltSettings=self.getEntry(bedBoltSettings, i),
                )
                if i == 0:
                    self.edgeCorner(edges[i], edges[i + 1], 90)
            self.edgeCorner(edges[i], "e", 90)

            self.corner(alpha, r)
            self.cc(callback, 2)
            self.step(edges[2].startwidth())
            edges[2](((x - r) ** 2 + (y - r) ** 2) ** 0.5)
            self.step(-edges[2].endwidth())
            self.corner(90 - alpha, r)
            self.edge(edges[0].startwidth())
            self.corner(90)
            self.context.stroke()

            self.moveTo(width - 2 * dx, height - 2 * dy, 180)
            if n % 2:
                self.moveTo(width)

        self.move(overallwidth, overallheight, move, label=label)

    def trapezoidWall(
        self, w, h0, h1, edges="eeee", callback=None, move=None, label=""
    ):
        """
        Rectangular trapezoidal wall

        :param w: width
        :param h0: left height
        :param h1: right height
        :param edges:  (Default value = "eee") bottom, right, left
        :param callback:  (Default value = None)
        :param move:  (Default value = None)
        :param label: rendered to identify parts, it is not meant to be cut or etched (Default value = "")
        """

        edges = [self.edges.get(e, e) for e in edges]

        overallwidth = w + edges[-1].spacing() + edges[1].spacing()
        overallheight = max(h0, h1) + edges[0].spacing()

        if self.move(overallwidth, overallheight, move, before=True):
            return

        a = math.degrees(math.atan((h1 - h0) / w))
        square = ((h0 - h1) ** 2 + w**2) ** 0.5

        self.moveTo(edges[-1].spacing(), edges[0].margin())
        self.cc(callback, 0, y=edges[0].startwidth())
        edges[0](w)
        self.edgeCorner(edges[0], edges[1], 90)
        self.cc(callback, 1, y=edges[1].startwidth())
        edges[1](h1)
        self.edgeCorner(edges[1], self.edges["e"], 90)
        self.corner(a)
        self.cc(callback, 2)
        edges[2](square)
        self.corner(-a)
        self.edgeCorner(self.edges["e"], edges[-1], 90)
        self.cc(callback, 3, y=edges[-1].startwidth())
        edges[3](h0)
        self.edgeCorner(edges[-1], edges[0], 90)

        self.move(overallwidth, overallheight, move, label=label)

    def trapezoidSideWall(
        self, w, h0, h1, edges="eeee", radius=0.0, callback=None, move=None, label=""
    ):
        """
        Rectangular trapezoidal wall

        :param w: width
        :param h0: left height
        :param h1: right height
        :param edges:  (Default value = "eeee") bottom, right, left
        :param radius: (Default value = 0.0) radius of upper corners
        :param callback:  (Default value = None)
        :param move:  (Default value = None)
        :param label: rendered to identify parts, it is not meant to be cut or etched (Default value = "")
        """

        edges = [self.edges.get(e, e) for e in edges]

        overallwidth = w + edges[-1].spacing() + edges[1].spacing()
        overallheight = max(h0, h1) + edges[0].spacing()

        if self.move(overallwidth, overallheight, move, before=True):
            return

        r = min(radius, abs(h0 - h1))
        ws = w - r
        if h0 > h1:
            ws += edges[1].endwidth()
        else:
            ws += edges[3].startwidth()
        hs = abs(h1 - h0) - r
        a = math.degrees(math.atan(hs / ws))
        square = (ws**2 + hs**2) ** 0.5

        self.moveTo(edges[-1].spacing(), edges[0].margin())
        self.cc(callback, 0, y=edges[0].startwidth())
        edges[0](w)
        self.edgeCorner(edges[0], edges[1], 90)
        self.cc(callback, 1, y=edges[1].startwidth())
        edges[1](h1)

        if h0 > h1:
            self.polyline(0, (90 - a, r))
            self.cc(callback, 2)
            edges[2](square)
            self.polyline(0, (a, r), edges[3].startwidth(), 90)
        else:
            self.polyline(0, 90, edges[1].endwidth(), (a, r))
            self.cc(callback, 2)
            edges[2](square)
            self.polyline(0, (90 - a, r))
        self.cc(callback, 3, y=edges[-1].startwidth())
        edges[3](h0)
        self.edgeCorner(edges[-1], edges[0], 90)

        self.move(overallwidth, overallheight, move, label=label)

    ### polygonWall and friends

    def _polygonWallExtend(self, borders, edges, close=False):
        posx, posy = 0, 0
        ext = [0.0] * 4
        angle = 0

        def checkpoint(ext, x, y):
            ext[0] = min(ext[0], x)
            ext[1] = min(ext[1], y)
            ext[2] = max(ext[2], x)
            ext[3] = max(ext[3], y)

        # trace edge margins
        nborders = []
        for i, val in enumerate(borders):
            if i % 2:
                nborders.append(val)
            else:
                edge = edges[(i // 2) % len(edges)]
                margin = edge.margin()
                try:
                    square = val[0]
                except TypeError:
                    square = val
                if margin:
                    nborders.extend(
                        [0.0, -90, margin, 90, square, 90, margin, -90, 0.0]
                    )
                else:
                    nborders.append(val)

        borders = nborders
        for i in range(len(borders)):
            if i % 2:
                try:
                    a, r = borders[i]
                except TypeError:
                    angle = (angle + borders[i]) % 360
                    continue
                if a > 0:
                    centerx = posx + r * math.cos(math.radians(angle + 90))
                    centery = posy + r * math.sin(math.radians(angle + 90))
                else:
                    centerx = posx + r * math.cos(math.radians(angle - 90))
                    centery = posy + r * math.sin(math.radians(angle - 90))

                for direction in (0, 90, 180, 270):
                    if a > 0 and angle <= direction and (angle + a) % 360 >= direction:
                        direction -= 90
                    elif (
                        a < 0 and angle >= direction and (angle + a) % 360 <= direction
                    ):
                        direction -= 90
                    else:
                        continue
                    checkpoint(
                        ext,
                        centerx + r * math.cos(math.radians(direction)),
                        centery + r * math.sin(math.radians(direction)),
                    )
                    # print("%4s %4s %4s %f %f" % (angle, direction+90, angle+a, centerx + r * math.cos(math.radians(direction)), centery + r * math.sin(math.radians(direction))))
                angle = (angle + a) % 360
                if a > 0:
                    posx = centerx + r * math.cos(math.radians(angle - 90))
                    posy = centery + r * math.sin(math.radians(angle - 90))
                else:
                    posx = centerx + r * math.cos(math.radians(angle + 90))
                    posy = centery + r * math.sin(math.radians(angle + 90))
            else:
                posx += borders[i] * math.cos(math.radians(angle))
                posy += borders[i] * math.sin(math.radians(angle))
            checkpoint(ext, posx, posy)

        return ext

    def _closePolygon(self, borders):
        posx, posy = 0, 0
        angle = 0.0

        if borders and borders[-1] is not None:
            return borders

        borders = borders[:-1]

        for i in range(len(borders)):
            if i % 2:
                try:
                    a, r = borders[i]
                except TypeError:
                    angle = (angle + borders[i]) % 360
                    continue
                if a > 0:
                    centerx = posx + r * math.cos(math.radians(angle + 90))
                    centery = posy + r * math.sin(math.radians(angle + 90))
                else:
                    centerx = posx + r * math.cos(math.radians(angle - 90))
                    centery = posy + r * math.sin(math.radians(angle - 90))

                angle = (angle + a) % 360
                if a > 0:
                    posx = centerx + r * math.cos(math.radians(angle - 90))
                    posy = centery + r * math.sin(math.radians(angle - 90))
                else:
                    posx = centerx + r * math.cos(math.radians(angle + 90))
                    posy = centery + r * math.sin(math.radians(angle + 90))
            else:
                posx += borders[i] * math.cos(math.radians(angle))
                posy += borders[i] * math.sin(math.radians(angle))
        if len(borders) % 2 == 0:
            borders.append(0.0)

        a = math.degrees(math.atan2(-posy, -posx))
        # print(a, angle, a - angle)
        borders.append((a - angle + 360) % 360)
        borders.append((posx**2 + posy**2) ** 0.5)
        borders.append(-a)
        # print(borders)
        return borders

    def polygonWall(
        self,
        borders,
        edge="f",
        turtle=False,
        correct_corners=True,
        callback=None,
        move=None,
        label="",
    ):
        """
        Polygon wall for all kind of multi-edged objects

        :param borders: array of distance and angles to draw
        :param edge:  (Default value = "f") Edges to apply. If the array of borders contains more segments that edges, the edge will wrap. Only edge types without start and end width supported for now.
        :param turtle: (Default value = False)
        :param correct_corners: (Default value = True)
        :param callback:  (Default value = None)
        :param move:  (Default value = None)
        :param label: rendered to identify parts, it is not meant to be cut or etched (Default value = "")

        borders is alternating between length of the edge and angle of the corner. For now neither tabs nor radii are supported. None at the end closes the polygon.
        """
        try:
            edges = [self.edges.get(e, e) for e in edge]
        except TypeError:
            edges = [self.edges.get(edge, edge)]

        t = self.thickness  # XXX edge.margin()

        borders = self._closePolygon(borders)

        minx, miny, maxx, maxy = self._polygonWallExtend(borders, edges)

        tw, th = maxx - minx, maxy - miny

        if not turtle:
            if self.move(tw, th, move, True):
                return

            self.moveTo(-minx, -miny)

        length_correction = 0.0
        for i in range(0, len(borders), 2):
            self.cc(callback, i // 2)
            self.edge(length_correction)
            square = borders[i] - length_correction
            next_angle = borders[i + 1]

            if (
                correct_corners
                and isinstance(next_angle, (int, float))
                and next_angle < 0
            ):
                length_correction = t * math.tan(math.radians(-next_angle / 2))
            else:
                length_correction = 0.0
            square -= length_correction
            edge = edges[(i // 2) % len(edges)]
            edge(square)
            self.edge(length_correction)
            self.corner(next_angle, tabs=1)

        if not turtle:
            self.move(tw, th, move, label=label)

    @restore
    def polygonWalls(self, borders, h, bottom="F", top="F", symmetrical=True):
        if not borders:
            return

        borders = self._closePolygon(borders)
        bottom = self.edges.get(bottom, bottom)
        top = self.edges.get(top, top)
        t = self.thickness  # XXX edge.margin()

        leftsettings = copy.deepcopy(self.edges["f"].settings)
        lf, lF, lh = leftsettings.edgeObjects(self, add=False)
        rightsettings = copy.deepcopy(self.edges["f"].settings)
        rf, rF, rh = rightsettings.edgeObjects(self, add=False)

        length_correction = 0.0
        angle = borders[-1]
        i = 0
        part_cnt = 0

        self.moveTo(0, bottom.margin())
        while i < len(borders):
            if symmetrical:
                if part_cnt % 2:
                    left, right = lf, rf
                else:
                    # last part of an uneven lot
                    if part_cnt == (len(borders) // 2) - 1:
                        left, right = lF, rf
                    else:
                        left, right = lF, rF
            else:
                left, right = lf, rF

            top_lengths = []
            top_edges = []

            self.moveTo(left.spacing() + self.spacing, 0)
            square = borders[i] - length_correction
            leftsettings.setValues(self.thickness, angle=angle)
            angle = borders[i + 1]

            while isinstance(angle, (tuple, list)):
                bottom(square)
                angle, radius = angle
                lr = abs(math.radians(angle) * radius)
                self.edges["X"](lr, h + 2 * t)  # XXX
                top_lengths.append(square)
                top_lengths.append(lr)
                top_edges.append(top)
                top_edges.append("E")

                i += 2
                square = borders[i]
                angle = borders[i + 1]

            rightsettings.setValues(self.thickness, angle=angle)
            if angle < 0:
                length_correction = t * math.tan(math.radians(-angle / 2))
            else:
                length_correction = 0.0
            square -= length_correction

            bottom(square)

            top_lengths.append(square)
            top_edges.append(top)
            with self.saved_context():
                self.edgeCorner(bottom, right, 90)
                right(h)
                self.edgeCorner(right, top, 90)

                top_edges.reverse()
                top_lengths.reverse()
                edges.CompoundEdge(self, top_edges, top_lengths)(sum(top_lengths))
                self.edgeCorner(top, left, 90)
                left(h)
                self.edgeCorner(left, bottom, 90)
                self.context.stroke()

            self.moveTo(right.spacing() + self.spacing)
            part_cnt += 1
            i += 2

    ##################################################
    ### Place Parts
    ##################################################

    def partsMatrix(self, n, width, move, part, *args, **kwargs):
        """place many of the same part

        :param n: number of parts
        :param width: number of parts in a row (0 for same as n)
        :param move: (Default value = "")
        :param part: callable that draws a part and knows move param
        :param l: params for part
        :param kw: keyword params for part
        """
        if n <= 0:
            return

        if not width:
            width = n

        rows = n // width + (1 if n % width else 0)

        if not move:
            move = ""
        move = move.split()

        # move down / left before
        for m in move:
            if m == "left":
                kwargs["move"] = "left only"
                for i in range(width):
                    part(*args, **kwargs)
            if m == "down":
                kwargs["move"] = "down only"
                for i in range(rows):
                    part(*args, **kwargs)
        # draw matrix
        for i in range(rows):
            with self.saved_context():
                for j in range(width):
                    if "only" in move:
                        break
                    if width * i + j >= n:
                        break
                    kwargs["move"] = "right"
                    part(*args, **kwargs)
            kwargs["move"] = "up only"
            part(*args, **kwargs)

        # Move back down
        if "up" not in move:
            kwargs["move"] = "down only"
            for i in range(rows):
                part(*args, **kwargs)

        # Move right
        if "right" in move:
            kwargs["move"] = "right only"
            for i in range(width):
                part(*args, **kwargs)

    def mirrorX(self, f, offset=0.0):
        """Wrap a function to draw mirrored at the y axis

        :param f: function to wrap
        :param offset: (default value = 0.0) axis to mirror at
        """

        def r():
            self.moveTo(offset, 0)
            with self.saved_context():
                self.context.scale(-1, 1)
                f()

        return r

    def mirrorY(self, f, offset=0.0):
        """Wrap a function to draw mirrored at the x axis

        :param f: function to wrap
        :param offset: (default value = 0.0) axis to mirror at
        """

        def r():
            self.moveTo(0, offset)
            with self.saved_context():
                self.context.scale(1, -1)
                f()

        return r
