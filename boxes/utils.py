import re
import argparse

from typing import List


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
        for key, arg in setting.get_arguments():
            setattr(box, key, arg)
