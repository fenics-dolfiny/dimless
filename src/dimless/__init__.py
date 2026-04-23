import json
from importlib.resources import files

_base = files("dimless").joinpath("data")
_numbers = _base.joinpath("numbers")


def quantities():
    return json.loads(_base.joinpath("quantities.json").read_text())


def number(key: str):
    return json.loads(_numbers.joinpath(f"{key}.json").read_text())


def search(text: str):
    text = text.lower()
    out = []
    for path in _numbers.iterdir():
        if path.suffix != ".json":
            continue
        obj = json.loads(path.read_text())
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
