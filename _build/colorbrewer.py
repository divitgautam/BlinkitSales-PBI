"""ColorBrewer 2.0 palettes for our Power BI and Python work (data: colorbrewer_schemes.txt, from colorbrewer2.org).

    import sys; sys.path.insert(0, r"D:\\Wolf\\PBI\\_knowledge")
    import colorbrewer as cb
    cb.get("BuGn", 5); cb.safe("div", 7); cb.pbi_gradient("RdBu", 7); cb.mpl_cmap("YlGnBu", 9)
"""
from pathlib import Path

_DATA = Path(__file__).with_name("colorbrewer_schemes.txt")
TYPES = {"seq": "sequential", "div": "diverging", "qual": "qualitative"}
SCHEMES: dict = {}


def _flag(s: str, n: int) -> int:
    return int(s[0]) if len(s) == 1 else (int(s[n - 3]) if 0 <= n - 3 < len(s) else 0)


for line in _DATA.read_text(encoding="utf-8").splitlines():
    if not line or line.startswith("#"):
        continue
    if "|" in line:
        name, kind, b, p, c, s = line.split("|")
        SCHEMES[name] = {"type": kind, "blind": b[1:], "print": p[1:], "copy": c[1:], "screen": s[1:], "colors": {}}
    else:
        key, hexes = line.split(":")
        name = next(n for n in sorted(SCHEMES, key=len, reverse=True) if key.startswith(n) and key[len(n):].isdigit())
        SCHEMES[name]["colors"][int(key[len(name):])] = ["#" + h for h in hexes.split(",")]


def get(name: str, n: int, reverse: bool = False) -> list:
    """Hex colours of scheme `name` with `n` classes (KeyError if that class count doesn't exist)."""
    cols = SCHEMES[name]["colors"][n]
    return cols[::-1] if reverse else list(cols)


def info(name: str, n: int) -> dict:
    """Safety flags at n classes: 1 safe, 2 maybe, 0 not safe."""
    s = SCHEMES[name]
    return {k: _flag(s[k], n) for k in ("blind", "print", "copy", "screen")} | {"type": TYPES[s["type"]]}


def safe(kind: str = None, n: int = 5, need=("blind",), allow_maybe: bool = False) -> list:
    """Scheme names of a type ('seq', 'div', 'qual') that pass every flag in `need` at n classes."""
    ok = {1, 2} if allow_maybe else {1}
    return [k for k, s in SCHEMES.items() if (kind is None or s["type"] == kind) and n in s["colors"]
            and all(_flag(s[f], n) in ok for f in need)]


def pbi_gradient(name: str, n: int = None) -> dict:
    """Min / (mid) / max colours for a Power BI conditional-format gradient (diverging schemes get a centre)."""
    s = SCHEMES[name]
    cols = s["colors"][n or max(s["colors"])]
    out = {"min": cols[0], "max": cols[-1]}
    if s["type"] == "div":
        out["mid"] = cols[len(cols) // 2]
    return out


def pbi_theme_colors(name: str, n: int) -> dict:
    """Snippet for a Power BI theme JSON: {"dataColors": [...]} (use for qualitative schemes)."""
    return {"dataColors": get(name, n)}


def mpl_cmap(name: str, n: int, reverse: bool = False):
    """matplotlib ListedColormap with exactly n ColorBrewer classes."""
    from matplotlib.colors import ListedColormap
    return ListedColormap(get(name, n, reverse), name=f"{name}{n}")


if __name__ == "__main__":
    print(len(SCHEMES), "schemes")
    print("BuGn 3:", get("BuGn", 3))
    print("colourblind-safe diverging at 7:", safe("div", 7))
    print("colourblind-safe qualitative at 3:", safe("qual", 3))
