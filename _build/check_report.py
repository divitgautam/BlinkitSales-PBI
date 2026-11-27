"""Static layout check of the generated PBIR report: bounds, overlaps, title and subtitle widths, alt text, tab order.
Run: python _build/check_report.py   (after build_report.py)"""
import json, os, re, sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.stdout.reconfigure(encoding="utf-8")
PAGES = ROOT / "BlinkitSales-PBI.Report" / "definition" / "pages"
CH_TITLE, CH_SUB = 7.7, 6.3          # px per character at 11 pt bold and 9 pt
CH_LABEL, CH_DELTA, DELTA_PAD = 6.0, 5.6, 48   # card label 10 pt; change line 9 pt bold; the line box loses ~48 px to padding (observed: 27 chars cut in a 198 px card)
CH_NAV, NAV_PAD, NAV_MIN_H = 4.9, 36, 32       # page-navigator tab: 8 pt text plus button padding; a 28 px pill clipped its labels
CH_FOOT, FOOT_PAD = 5.2, 40                    # footer text 8 pt bold; observed cut-off of a 112-character footer in a 540 px box
BAR_ROW, BAR_CHROME, BAR_CHROME_NOSUB = 26, 75, 50   # bar chart: min px per category before a scrollbar appears; title+subtitle+padding+axis
PIV_CHROME, PIV_CHROME_NOSUB, PIV_PAD, PIV_CELL = 62, 50, 2, 8   # pivot: title(+subtitle) chrome; default row padding px; per-cell horizontal padding px
PIV_ROW_EXTRA = 8                              # pivot row px = 1.333 x font pt + 2 x row padding + 8 (about 22 px at 8 pt with padding 2; the heat map scrolled at ~18.5 px/row in a 204 px body)
CW_REG, CW_BOLD = 0.52, 0.58                   # glyph width as a share of the font px (pt x 1.333); regular / bold
SPEC = Path(os.environ.get("CHECK_SPEC", ROOT / "_build" / "measures_spec.py")).read_text(encoding="utf-8")   # CHECK_SPEC: test against another spec version


def footer_chars():
    """Rendered length of the Footer Text measure: its string literals plus the width of each date format."""
    blk = SPEC[SPEC.index('add("Footer Text",') + 17:]
    blk = blk[:blk.index("None, P")]
    lits = [m for m in re.findall(r'"([^"]*)"', blk) if m != "en-US"]
    widths = {"d mmm yyyy": 11, "mmm yyyy": 8}
    return sum(widths.get(m, len(m)) for m in lits)


def delta_chars(measure):
    """Longest change line of a card: arrow + size + ' Oct 24 vs Oct 23'. Looked up from the yoy() table in measures_spec."""
    nm = measure.replace("Δ ", "")
    m = re.search(r'\("' + re.escape(nm) + r'", "[^"]*", "(rel|pp|abs)", "[a-z]+", "([^"]*)"\)', SPEC)
    if nm in ("Revenue", "Orders", "AOV"): return 2 + 5 + 17
    if not m: return 27
    size = {"rel": 5, "pp": 6, "abs": 4 + (len(m.group(2)) + 1 if m.group(2) else 0)}[m.group(1)]
    return 2 + size + 17
PAGE_BOTTOM, FOOT_BOTTOM, MARGIN = 38, 4, 16   # content must end 38 px above the page bottom (footer zone); footer 4 px above it
ROW_PX, CHROME_PX, SCROLLBAR_PX = 18, 62, 14   # px per category row, title + subtitle, horizontal scrollbar
PHINTS = json.loads((ROOT / "_build" / "pivot_hints.json").read_text(encoding="utf-8")) if (ROOT / "_build" / "pivot_hints.json").exists() else {}
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
                dm = v["visual"]["query"]["queryState"]["Data"]["projections"][0]["field"]["Measure"]["Property"]
                dn = delta_chars(dm)
                if dn * CH_DELTA > w - DELTA_PAD: bad.append(f"{pg['name']}/{n_}: change line '{dm}' (up to {dn} chars) needs {dn * CH_DELTA:.0f}px of {w - DELTA_PAD}")
            else:
                lab = v["visual"]["query"]["queryState"]["Data"]["projections"][0].get("displayName", "")
                if len(lab) * CH_LABEL > w - 34: bad.append(f"{pg['name']}/{n_}: card label '{lab}' needs {len(lab) * CH_LABEL:.0f}px of {w - 34}")
                if n_ + "_d" in {x_["name"] for x_ in vis}:
                    pad = vc.get("padding", [{}])[0].get("properties", {}).get("bottom", {}).get("expr", {}).get("Literal", {}).get("Value", "0D")
                    if float(pad.rstrip("DL")) < 24: bad.append(f"{pg['name']}/{n_}: bottom padding {pad} leaves the value under the change line (need 24+)")
        if n_ == "ftr_text":
            fc = int(os.environ.get("FOOT_CHARS", footer_chars()))
            if fc * CH_FOOT + FOOT_PAD > w: bad.append(f"{pg['name']}/{n_}: footer text ({fc} chars) needs {fc * CH_FOOT + FOOT_PAD:.0f}px of {w}")
            nav = next((o for o in vis if o["name"] == "ftr_nav"), None)
            if nav and x + w > nav["position"]["x"] + 0.5: bad.append(f"{pg['name']}/{n_}: footer text box overlaps the navigator")
        if vt == "pageNavigator":
            if h < NAV_MIN_H: bad.append(f"{pg['name']}/{n_}: navigator is {h}px high, labels clip below {NAV_MIN_H}")
            tabs = [names[k] for k in json.loads((PAGES / "pages.json").read_text(encoding="utf-8"))["pageOrder"] if k in names]
            need = max(len(t) for t in tabs) * CH_NAV + NAV_PAD
            if need * len(tabs) > w: bad.append(f"{pg['name']}/{n_}: {len(tabs)} tabs need {need:.0f}px each ({need * len(tabs):.0f}px), nav is {w}px wide")
        hk = HINTS.get(f"{pg['name']}/{n_}")
        has_sub = bool(v["visual"].get("visualContainerObjects", {}).get("subTitle", [{}])[0].get("properties", {}).get("text"))
        if vt in ("clusteredBarChart", "pivotTable") and pg.get("type") != "Tooltip" and not hk:
            bad.append(f"{pg['name']}/{n_}: list visual without a row count in row_hints.json (add hint() in build_report.py)")
        if hk and vt == "clusteredBarChart":
            need = (BAR_CHROME if has_sub else BAR_CHROME_NOSUB) + BAR_ROW * hk
            if need > h: bad.append(f"{pg['name']}/{n_}: {hk} bars need ~{need}px, visual is {h}px (would scroll)")
        elif hk and vt == "pivotTable":
            ob = v["visual"].get("objects", {})
            lit = lambda grp, key, dflt: float(ob.get(grp, [{}])[0].get("properties", {}).get(key, {}).get("expr", {}).get("Literal", {}).get("Value", dflt).rstrip("D"))
            fs, fh, pad = lit("values", "fontSize", "10D"), lit("columnHeaders", "fontSize", "10D"), lit("grid", "rowPadding", f"{PIV_PAD}D")
            need = (PIV_CHROME if has_sub else PIV_CHROME_NOSUB) + (fs * 1.333 + 2 * pad + PIV_ROW_EXTRA) * (hk + 1)
            if need > h: bad.append(f"{pg['name']}/{n_}: {hk} rows + header at {fs:.0f} pt need ~{need:.0f}px, visual is {h}px (would scroll)")
            ph = PHINTS.get(f"{pg['name']}/{n_}")
            if ph:   # (a) column header text must fit its column; all columns plus the row header must fit the visual width
                wrap = ob.get("columnHeaders", [{}])[0].get("properties", {}).get("wordWrap", {}).get("expr", {}).get("Literal", {}).get("Value") == "true"
                bw = lambda t: len(t) * CW_BOLD * fh * 1.333
                cols = []
                for i, c_ in enumerate(ph["cols"]):
                    val = ph["values"][i if ph.get("colvalues") else 0]
                    hdr = max((len(x_) for x_ in c_.split()), default=0) * CW_BOLD * fh * 1.333 if wrap else bw(c_)
                    cols.append(max(hdr, len(val) * CW_REG * fs * 1.333) + PIV_CELL)
                rowhdr = max(len(r_) for r_ in ph["rows"]) * CW_REG * fs * 1.333 + PIV_CELL
                tot = rowhdr + sum(cols) + 24
                if tot > w: bad.append(f"{pg['name']}/{n_}: row header + {len(cols)} columns need ~{tot:.0f}px of {w} (headers {ph['cols']}; widest column {max(cols):.0f}px) - a header would truncate or scroll")
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
        ttl_s = txt.get("Literal", {}).get("Value", "").strip("'") if "Literal" in txt else ""
        if ttl_s and s2 and re.sub(r"\W+", " ", ttl_s).lower() == re.sub(r"\W+", " ", s2).lower():
            bad.append(f"{pg['name']}/{v['name']}: title and subtitle say the same ('{s2}')")
        sub_off = st.get("show", {}).get("expr", {}).get("Literal", {}).get("Value") == "false"
        if txt and not s2 and not sub_off and vt not in ("textbox", "cardVisual", "slicer", "image", "pageNavigator") and not n_.startswith(("hdr_", "ftr_")):
            bad.append(f"{pg['name']}/{v['name']}: title with no explicit subtitle setting; Desktop adds an auto subtitle (e.g. 'ROAS by Campaign Name') that repeats the title - set subTitle show=false")
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
