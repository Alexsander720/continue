"""Helper for card parsers (written by Claude; do not edit). Facts that remember which proven field they show.

    F = Facts()
    F.sfact("max_health", "mask", "Маски", masks)      # label is the only place Russian text may be typed
    return finish({... "facts": F.items, "fact_sources": F.sources, ...}, path)
"""
import sys

sys.path.insert(0, str(__import__('pathlib').Path(__file__).resolve().parents[1]))
from ddsaves._common import dur, empty, fact, finish, num  # noqa: E402,F401


class Facts:
    def __init__(self):
        self.items, self.sources = [], {}

    def sfact(self, field, icon, label, value):
        item = fact(icon, label, value, id=field)
        self.items.append(item)
        self.sources[item["label"]] = field
