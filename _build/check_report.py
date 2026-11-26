"""Static layout check of the generated PBIR report: bounds, overlaps, title and subtitle widths, alt text, tab order.
Run: python _build/check_report.py   (after build_report.py)"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "BlinkitSales-PBI.Report" / "definition" / "pages"
CH_TITLE, CH_SUB = 7.7, 6.3          # px per character at 11 pt bold and 9 pt
bad = []
for pdir in sorted(d for d in PAGES.iterdir() if d.is_dir()):
    pg = json.loads((pdir / "page.json").read_text(encoding="utf-8"))
    W, H = pg["width"], pg["height"]
    vis = [json.loads((v / "visual.json").read_text(encoding="utf-8")) for v in sorted((pdir / "visuals").iterdir())]
    boxes = []
    for v in vis:
        pos = v["position"]
        x, y, w, h = pos["x"], pos["y"], pos["width"], pos["height"]
        if x < 0 or y < 0 or x + w > W + 0.5 or y + h > H + 0.5:
            bad.append(f"{pg['name']}/{v['name']}: outside page ({x},{y},{w},{h})")
        vco = v["visual"].get("visualContainerObjects", {})
        t = vco.get("title", [{}])[0].get("properties", {})
        st = vco.get("subTitle", [{}])[0].get("properties", {})
        txt = t.get("text", {}).get("expr", {})
        if "Literal" in txt and v["visual"]["visualType"] not in ("textbox",):
            s = txt["Literal"]["Value"].strip("'")
            if len(s) * CH_TITLE > w - 24:
                bad.append(f"{pg['name']}/{v['name']}: title {len(s)} chars needs {len(s) * CH_TITLE:.0f}px of {w - 24}")
        elif "Measure" in txt and 70 * CH_TITLE > w - 24:
            bad.append(f"{pg['name']}/{v['name']}: measure title (70 chars) needs {70 * CH_TITLE:.0f}px of {w - 24}")
        s2 = st.get("text", {}).get("expr", {}).get("Literal", {}).get("Value", "").strip("'")
        if s2 and len(s2) * CH_SUB > w - 24:
            bad.append(f"{pg['name']}/{v['name']}: subtitle {len(s2)} chars needs {len(s2) * CH_SUB:.0f}px of {w - 24}")
        if not any("altText" in x_.get("properties", {}) for x_ in vco.get("general", [])):
            bad.append(f"{pg['name']}/{v['name']}: no alt text")
        n = v["name"]
        if not (n.startswith(("hdr_", "ftr_", "slc_")) or n.endswith("_d")):
            boxes.append((n, x, y, w, h))
    for i, a in enumerate(boxes):
        for b in boxes[i + 1:]:
            if a[1] < b[1] + b[3] - 0.5 and b[1] < a[1] + a[3] - 0.5 and a[2] < b[2] + b[4] - 0.5 and b[2] < a[2] + a[4] - 0.5:
                bad.append(f"{pg['name']}: {a[0]} overlaps {b[0]}")
    print(f"{pg['name']:16} {len(vis):3} visuals")
print("\n".join(bad) if bad else "layout OK: all visuals inside pages, no overlaps, titles and subtitles fit, alt text everywhere")
