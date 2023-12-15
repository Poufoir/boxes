import re
from typing import Any


class Settings:
    """Generic Settings class

    Used by different other classes to store measurements and details.
    Supports absolute values and settings that grow with the thickness
    of the material used.

    Overload the absolute_params and relative_params class attributes with
    the supported keys and default values. The values are available via
    attribute access.
    """

    absolute_params: dict[str, Any] = {}  # TODO find better typing.
    relative_params: dict[str, Any] = {}  # TODO find better typing.

    @classmethod
    def get_arguments(cls, prefix=None, **defaults):
        prefix = prefix or cls.__name__[: -len("Settings")]

        lines = cls.__doc__.split("\n")

        # Parse doc string
        descriptions = {}
        r = re.compile(r"^ +\* +(\S+) +: .* : +(.*)")
        for line in lines:
            m = r.search(line)
            if m:
                descriptions[m.group(1)] = m.group(2)

        group = []
        for name, default in sorted(cls.absolute_params.items()) + sorted(
            cls.relative_params.items()
        ):
            # Handle choices
            if isinstance(default, tuple):
                t = type(default[0])
                for val in default:
                    if not isinstance(val, t) or not isinstance(
                        val, (bool, int, float, str)
                    ):
                        raise ValueError("Type not supported: %r", val)
                default = default[0]

            # Overwrite default
            if name in defaults:
                default = type(default)(defaults[name])

            if not isinstance(default, (bool, int, float, str)):
                raise ValueError("Type not supported: %r", default)
            group.append((f"{prefix}_{name}", default))
        return group

    def __init__(self, thickness, relative: bool = True, **kw) -> None:
        self.values = {}
        for name, value in self.absolute_params.items():
            if isinstance(value, tuple):
                value = value[0]
            if type(value) not in (bool, int, float, str):
                raise ValueError("Type not supported: %r", value)
            self.values[name] = value

        self.thickness = thickness
        factor = 1.0
        if relative:
            factor = thickness
        for name, value in self.relative_params.items():
            self.values[name] = value * factor
        self.setValues(thickness, relative, **kw)

    def edgeObjects(self, boxes, chars: str = "", add: bool = True):
        """
        Generate Edge objects using this kind of settings

        :param boxes: Boxes object
        :param chars: sequence of chars to be used by Edge objects
        :param add: add the resulting Edge objects to the Boxes object's edges
        """
        edges: list[Any] = []
        return self._edgeObjects(edges, boxes, chars, add)

    def _edgeObjects(self, edges, boxes, chars: str, add: bool):
        for i, edge in enumerate(edges):
            try:
                char = chars[i]
                edge.char = char
            except IndexError:
                pass
            except TypeError:
                pass
        if add:
            boxes.addParts(edges)
        return edges

    def setValues(self, thickness, relative: bool = True, **kw):
        """
        Set values

        :param thickness: thickness of the material used
        :param relative: Do scale by thickness (Default value = True)
        :param kw: parameters to set
        """
        factor = 1.0
        if relative:
            factor = thickness
        for name, value in kw.items():
            if name in self.absolute_params:
                self.values[name] = value
            elif name in self.relative_params:
                self.values[name] = value * factor
            else:
                raise ValueError(
                    f"Unknown parameter for {self.__class__.__name__}: {name}"
                )
        self.checkValues()

    def checkValues(self) -> None:
        """
        Check if all values are in the right range. Raise ValueError if needed.
        """
        pass

    def __getattr__(self, name):
        if "values" in self.__dict__ and name in self.values:
            return self.values[name]
        raise AttributeError


class HexHolesSettings(Settings):
    """Settings for hexagonal hole patterns

    Values:

    * absolute
      * diameter : 5.0 : diameter of the holes
      * distance : 3.0 : distance between the holes
      * style : "circle" : currently only supported style
    """

    absolute_params = {
        "diameter": 10.0,
        "distance": 3.0,
        "style": ("circle",),
    }

    relative_params: dict[str, Any] = {}


class fillHolesSettings(Settings):
    """Settings for Hole filling

    Values:

    * absolute
      * fill_pattern :        "no fill" : style of hole pattern
      * hole_style :          "round" : style of holes (does not apply to fill patterns 'vbar' and 'hbar')
      * max_random :          1000 : maximum number of random holes
      * bar_length :          50 : maximum length of bars
      * hole_max_radius :     12.0 : maximum radius of generated holes (in mm)
      * hole_min_radius :     4.0 : minimum radius of generated holes (in mm)
      * space_between_holes : 4.0 : hole to hole spacing (in mm)
      * space_to_border :     4.0 : hole to border spacing (in mm)
    """

    absolute_params = {
        "fill_pattern": ("no fill", "hex", "square", "random", "hbar", "vbar"),
        "hole_style": ("round", "triangle", "square", "hexagon", "octagon"),
        "max_random": 1000,
        "bar_length": 50,
        "hole_max_radius": 3.0,
        "hole_min_radius": 0.5,
        "space_between_holes": 4.0,
        "space_to_border": 4.0,
    }
