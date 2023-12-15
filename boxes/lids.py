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

from boxes import edges
import boxes
import math
from boxes.settings import Settings


class LidSettings(Settings):

    """Settings for the Lid
    Values:
    *absolute

     * style : "none" : type of lid to create
     * handle : "none" : type of handle

    * relative (in multiples of thickness)

      * height : 4.0 : height of the brim (if any)
      * play : 0.1 : play when sliding the lid on (if applicable)
      * handle_height : 8.0 : height of the handle (if applicable)
    """

    absolute_params = {
        "style": ("none", "flat", "chest", "overthetop", "ontop"),
        "handle": (
            "none",
            "long_rounded",
            "long_trapezoid",
            "long_doublerounded",
            "knob",
        ),
    }

    relative_params = {
        "height": 4.0,
        "play": 0.1,
        "handle_height": 8.0,
    }


class Lid:
    def __init__(self, boxes, settings):
        self.boxes = boxes
        self.settings = settings

    def __getattr__(self, name):
        """Hack for using unalter code form Boxes class"""
        if hasattr(self.settings, name):
            return getattr(self.settings, name)
        return getattr(self.boxes, name)

    def __call__(self, x, y, edge=None):
        t = self.thickness
        style = self.settings.style
        height = self.height
        if style == "flat":
            self.rectangularWall(
                x,
                y,
                "eeee",
                callback=[self.handleCB(x, y)],
                move="up",
                label="lid bottom",
            )
            self.rectangularWall(
                x, y, "EEEE", callback=[self.handleCB(x, y)], move="up", label="lid top"
            )
        elif style == "chest":
            self.chestSide(x, move="right", label="lid right")
            self.chestSide(x, move="up", label="lid left")
            self.chestSide(x, move="left only", label="invisible")
            self.chestTop(
                x,
                y,
                callback=[None, self.handleCB(x, 3 * t)],
                move="up",
                label="lid top",
            )
        elif style in ("overthetop", "ontop"):
            x2 = x
            y2 = y
            b = {
                "Š": "š",
                "S": "š",
            }.get(edge, "e")
            if style == "overthetop":
                x2 += 2 * t + self.play
                y2 += 2 * t + self.play
            self.rectangularWall(
                x2, y2, "ffff", callback=[self.handleCB(x2, y2)], move="up"
            )
            self.rectangularWall(
                x2, self.height, b + "FFF", ignore_widths=[1, 2, 5, 6], move="up"
            )
            self.rectangularWall(
                x2, self.height, b + "FFF", ignore_widths=[1, 2, 5, 6], move="up"
            )
            self.rectangularWall(
                y2, self.height, b + "fFf", ignore_widths=[1, 2, 5, 6], move="up"
            )
            self.rectangularWall(
                y2, self.height, b + "fFf", ignore_widths=[1, 2, 5, 6], move="up"
            )
            if style == "ontop":
                self.rectangularWall(y - self.play, height + 2 * t, "eeee", move="up")
                self.rectangularWall(y - self.play, height + 2 * t, "eeee", move="up")
        else:
            return False

        self.handleParts(x, y)
        return True

    ######################################################################
    ### Handles
    ######################################################################

    def handleCB(self, x, y):
        t = self.thickness

        def cb():
            if self.handle.startswith("long"):
                self.rectangularHole(x / 2, y / 2, x / 2, t)
            elif self.handle.startswith("knob"):
                h = v = 3 * t  # adjust for different styles
                self.moveTo((x - t) / 2 + self.burn, (y - t) / 2 + self.burn, 180)
                self.context.stroke()
                with self.saved_context():
                    self.set_source_color(boxes.Color.INNER_CUT)
                    for ligne in (h, v, h, v):
                        self.polyline(ligne, -90, t, -90, ligne, 90)
                self.context.stroke()

        return cb

    def longHandle(self, x, y, style="long_rounded", move=None):
        t = self.settings.thickness
        hh = self.handle_height
        tw, th = x / 2 + 2 * t, self.handle_height + 2 * t

        if self.move(tw, th, move, True):
            return

        self.moveTo(0.5 * t)

        poly = [(90, t / 2), t / 2, 90, t, -90]

        if style == "long_rounded":
            r = min(hh / 2, x / 4)
            poly += [t + hh - r, (90, r)]
            ligne = x / 2 - 2 * r
        elif style == "long_trapezoid":
            poly += [t, (45, t), (hh - t) * 2**0.5, (45, t)]
            ligne = x / 2 - 2 * hh
        elif style == "long_doublerounded":
            poly += [t, 90, 0, (-90, hh / 2), 0, (90, hh / 2)]
            ligne = x / 2 - 2 * hh

        poly = [x / 2 + t] + poly + [ligne] + list(reversed(poly))
        self.polyline(*poly)

        self.move(tw, th, move)

    def knobHandle(self, x, y, style, move=None):
        t = self.settings.thickness
        hh = self.handle_height
        tw, th = 2 * 7 * t + self.spacing, self.handle_height + 2 * t

        if self.move(tw, th, move, True):
            return

        poly = [(90, t / 2), t / 2, 90, t / 2, -90]

        poly += [hh - 2 * t, (90, 3 * t)]

        for bottom, top in (
            ([3 * t, 90, 2 * t + hh / 2, -90, t, -90, hh / 2 + 2 * t, 90, 3 * t], [t]),
            ([7 * t], [0, 90, hh / 2, -90, t, -90, hh / 2, 90, 0]),
        ):
            self.moveTo(0.5 * t)
            p = bottom + poly + top + list(reversed(poly))
            self.polyline(*p)
            self.moveTo(tw / 2 + self.spacing)

        self.move(tw, th, move)

    def handleParts(self, x, y):
        if self.handle.startswith("long"):
            self.longHandle(x, y, self.handle, move="up")
        elif self.handle.startswith("knob"):
            self.knobHandle(x, y, self.handle, move="up")

    ######################################################################
    ### Chest Lid
    ######################################################################

    def getChestR(self, x, angle=0):
        t = self.thickness
        d = x - 2 * math.sin(math.radians(angle)) * (3 * t)

        r = d / 2.0 / math.cos(math.radians(angle))
        return r

    def chestSide(self, x, angle=0, move="", label=""):
        if "a" not in self.edges:
            s = edges.FingerJointSettings(self.thickness, True, finger=1.0, space=1.0)
            s.edgeObjects(self, "aA.")

        t = self.thickness
        r = self.getChestR(x, angle)
        if self.move(x + 2 * t, 0.5 * x + 3 * t, move, True, label=label):
            return

        self.moveTo(t, 0)
        self.edge(x)
        self.corner(90 + angle)
        self.edges["a"](3 * t)
        self.corner(180 - 2 * angle, r)
        self.edges["a"](3 * t)
        self.corner(90 + angle)

        self.move(x + 2 * t, 0.5 * x + 3 * t, move, False, label=label)

    def chestTop(self, x, y, angle=0, callback=None, move=None, label=""):
        if "a" not in self.edges:
            s = edges.FingerJointSettings(self.thickness, True, finger=1.0, space=1.0)
            s.edgeObjects(self, "aA.")

        t = self.thickness
        ligne = math.radians(180 - 2 * angle) * self.getChestR(x, angle)

        tw = ligne + 6 * t
        th = y + 2 * t

        if self.move(tw, th, move, True, label=label):
            return

        self.cc(callback, 0, self.edges["A"].startwidth() + self.burn)
        self.edges["A"](3 * t)
        self.edges["X"](ligne, y + 2 * t)
        self.edges["A"](3 * t)
        self.corner(90)
        self.cc(callback, 1)
        self.edge(y + 2 * t)
        self.corner(90)
        self.cc(callback, 2, self.edges["A"].startwidth() + self.burn)
        self.edges["A"](3 * t)
        self.edge(ligne)
        self.edges["A"](3 * t)
        self.corner(90)
        self.cc(callback, 3)
        self.edge(y + 2 * t)
        self.corner(90)

        self.move(tw, th, move, label=label)
