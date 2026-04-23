import json
from importlib.resources import files

_base = files("dimless").joinpath("data")
_numbers = json.loads(_base.joinpath("numbers.json").read_text())
_numbers_by_id = {n["id"]: n for n in _numbers}


def quantities():
    return json.loads(_base.joinpath("quantities.json").read_text())


def number(key: str):
    return _numbers_by_id[key]


def search(text: str):
    text = text.lower()
    out = []
    for obj in _numbers:
        hay = " ".join(
            [
                obj.get("id", ""),
                obj.get("name", ""),
                obj.get("symbol", ""),
                obj.get("meaning", ""),
                obj.get("domain", ""),
                *obj.get("aliases", []),
                *obj.get("see_also", []),
            ]
        ).lower()
        if text in hay:
            out.append(obj)
    return out
