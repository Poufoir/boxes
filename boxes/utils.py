import re
import argparse

from typing import List, Dict


def dist(dx: float, dy: float):
    """
    Return distance

    :param dx: delta x
    :param dy: delay y
    """
    return (dx**2 + dy**2) ** 0.5


def argparseSections(s: str, group: int = 3):
    """
    Parse sections parameter

    :param s: string to parse
    """

    result: List[float] = []

    s = re.split(r"\s|:", s)

    try:
        for part in s:
            m = re.match(r"^(\d+(\.\d+)?)/(\d+)$", part)
            if m:
                n = int(m.group(group))
                result.extend([float(m.group(1)) / n] * n)
                continue
            m = re.match(r"^(\d+(\.\d+)?)\*(\d+)$", part)
            if m:
                n = int(m.group(group))
                result.extend([float(m.group(1))] * n)
                continue
            result.append(float(part))
    except ValueError:
        print(s)
        raise argparse.ArgumentTypeError("Don't understand sections string")

    if not result:
        result.append(0.0)

    return result


def edge_init(box, list_edges: List):
    for setting in list_edges:
        if isinstance(setting, Dict):
            setting_name = setting["setting"]
            args = setting["args"]
            prefix = setting_name.__name__[: -len("Settings")]
            box.edgesettings[prefix] = {}
            for key, arg in setting_name.get_arguments(**args):
                box.edgesettings[prefix][key[len(prefix) + 1 :]] = arg
                setattr(box, key, arg)
        else:
            for key, arg in setting.get_arguments():
                setattr(box, key, arg)
