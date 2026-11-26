"""Static layout check of the generated PBIR report: bounds, overlaps, title and subtitle widths, alt text, tab order.
Run: python _build/check_report.py   (after build_report.py)"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PAGES = ROOT / "BlinkitSales-PBI.Report" / "definition" / "pages"
CH_TITLE, CH_SUB = 7.7, 6.3          # px per character at 11 pt bold and 9 pt
CH_LABEL, CH_DELTA, DELTA_MAX = 6.0, 6.0, 27   # card label 10 pt, change line 9 pt (longest generated line is 27 characters)
CH_NAV, NAV_PAD = 4.9, 36                      # page-navigator tab: 8 pt text plus button padding
PAGE_BOTTOM, FOOT_BOTTOM, MARGIN = 38, 4, 16   # content must end 38 px above the page bottom (footer zone); footer 4 px above it
ROW_PX, CHROME_PX, SCROLLBAR_PX = 18, 62, 14   # px per category row, title + subtitle, horizontal scrollbar
HINTS = json.loads((ROOT / "_build" / "row_hints.json").read_text(encoding="utf-8")) if (ROOT / "_build" / "row_hints.json").exists() else {}
bad = []
names = {}
for d in PAGES.iterdir():
    if d.is_dir():
        pj = json.loads((d / "page.json").read_text(encoding="utf-8"))
        if pj.get("visibility") != "HiddenInViewMode":
            names[pj["name"]] = pj["displayName"]
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
        n_ = v["name"]
        vt = v["visual"]["visualType"]
        if pg.get("type") not in ("Tooltip",):
            if n_.startswith("ftr_"):
                if y + h > H - FOOT_BOTTOM + 0.5: bad.append(f"{pg['name']}/{n_}: footer ends {H - y - h:.0f}px above page bottom, needs {FOOT_BOTTOM}")
            elif not n_.startswith(("hdr_",)) and (y + h > H - PAGE_BOTTOM + 0.5 or x + w > W - MARGIN + 0.5 or x < MARGIN - 0.5):
                bad.append(f"{pg['name']}/{n_}: inside the margin zone (bottom {H - y - h:.0f}px, right {W - x - w:.0f}px, left {x:.0f}px; need {PAGE_BOTTOM}/{MARGIN}/{MARGIN})")
        if vt == "cardVisual" and not n_.startswith(("ftr_", "hdr_")) and pg.get("type") != "Tooltip":
            vc = v["visual"].get("visualContainerObjects", {})
            if n_.endswith("_d"):
                if DELTA_MAX * CH_DELTA > w - 14: bad.append(f"{pg['name']}/{n_}: change line (up to {DELTA_MAX} chars) needs {DELTA_MAX * CH_DELTA:.0f}px of {w - 14}")
            else:
                lab = v["visual"]["query"]["queryState"]["Data"]["projections"][0].get("displayName", "")
                if len(lab) * CH_LABEL > w - 34: bad.append(f"{pg['name']}/{n_}: card label '{lab}' needs {len(lab) * CH_LABEL:.0f}px of {w - 34}")
                if n_ + "_d" in {x_["name"] for x_ in vis}:
                    pad = vc.get("padding", [{}])[0].get("properties", {}).get("bottom", {}).get("expr", {}).get("Literal", {}).get("Value", "0D")
                    if float(pad.rstrip("DL")) < 24: bad.append(f"{pg['name']}/{n_}: bottom padding {pad} leaves the value under the change line (need 24+)")
        if vt == "pageNavigator":
            tabs = [names[k] for k in json.loads((PAGES / "pages.json").read_text(encoding="utf-8"))["pageOrder"] if k in names]
            need = max(len(t) for t in tabs) * CH_NAV + NAV_PAD
            if need * len(tabs) > w: bad.append(f"{pg['name']}/{n_}: {len(tabs)} tabs need {need:.0f}px each ({need * len(tabs):.0f}px), nav is {w}px wide")
        hk = HINTS.get(f"{pg['name']}/{n_}")
        if hk and vt in ("clusteredBarChart", "clusteredColumnChart", "pivotTable"):
            if vt == "clusteredColumnChart": pass
            else:
                need = CHROME_PX + ROW_PX * (hk + (1 if vt == "pivotTable" else 0)) + (SCROLLBAR_PX if vt == "pivotTable" else 0)
                if need > h: bad.append(f"{pg['name']}/{n_}: {hk} rows need ~{need}px, visual is {h}px (would scroll)")
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
