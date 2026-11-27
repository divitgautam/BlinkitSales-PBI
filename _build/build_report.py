"""Builds the BlinkitSales-PBI report pages (PBIR JSON) in the QuickCommerce theme (_build/blinkit_theme.py) on the shared kit pbir_kit.py.
Run with Power BI Desktop CLOSED:  python _build/build_report.py   (needs data/clean/*.csv, forecast.csv, levers.csv, report_facts.json)

Pages: 1 Overview, 2 Sales, 3 Delivery, 4 Experience, 5 Marketing, 6 Insights, 7 Forecast, plus hidden Category detail and Campaign detail
drill-through pages and two tooltip pages. Every headline is a DAX title measure (folder 8 Titles); static chart titles state fixed facts."""
import json
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent))
import pbir_kit as k
import blinkit_theme as th
th.apply(k)
from pbir_kit import (L, C, col, mea, qref, cat_filter, series_color_by_value, series_color_by_measure, Page, NO_CHROME,
                      TEAL, AMBER, CORAL, INK, MUTED, WHITE, LINE, W, H, M, G)

ROOT = Path(__file__).resolve().parents[1]
k.init(ROOT / "BlinkitSales-PBI.Report")
CLEAN = ROOT / "data" / "clean"
GREEN, GOLD, GREY, YELLOW = th.GREEN, th.GOLD, th.GREY, th.YELLOW
FACTS = json.loads((CLEAN / "report_facts.json").read_text(encoding="utf-8"))

# ------------------------------------------------------------------ numbers for the static text (same data as docs/reconciliation.md)
fo = pd.read_csv(CLEAN / "fact_orders.csv")
lv = pd.read_csv(CLEAN / "levers.csv")
inr = lambda v: (f"₹{v / 1e7:.2f} Cr" if abs(v) >= 1e7 else f"₹{v / 1e5:.2f} L" if abs(v) >= 1e5 else f"₹{v:,.0f}")
rev, n = fo.order_total.sum(), len(fo)
late_rate, ontime = fo.is_late.mean(), (fo.delivery_status == "On Time").mean()
avg_late = fo.loc[fo.is_late, "minutes_late"].mean()
rar = fo.loc[fo.poor_experience, "order_total"].sum()
slight, sig = (fo.delivery_status == "Slightly Delayed").mean(), (fo.delivery_status == "Significantly Delayed").mean()
hr = fo.groupby("order_hour").is_late.mean()
on_time_traffic = int(((fo.delivery_status == "On Time") & fo.delay_reason.notna()).sum())
partial = fo.groupby("month_start").size()
fm_lo, fm_hi = fo[fo.is_full_month].groupby("month_start").order_total.sum().agg(["min", "max"])
mk = pd.read_csv(CLEAN / "fact_marketing.csv")
mch = mk.groupby("channel")[["spend", "attributed_revenue"]].sum()
mch["roas"] = mch.attributed_revenue / mch.spend
lev = {r.lever: r for r in lv.itertuples()}

# ------------------------------------------------------------------ fields
YM, MS, MONTH = col("Date", "Year Month"), col("Date", "Month Start"), col("Date", "Month")
CAT, PROD, PAY = col("dim_product", "Category"), col("dim_product", "Product Label"), col("fact_orders", "Payment Method")
STATUS, HOUR, RATING = col("fact_orders", "Delivery Status"), col("fact_orders", "Order Hour"), col("fact_orders", "Rating")
BAND, XCLASS, FBCAT, SENT = col("fact_orders", "Minutes Late Band"), col("fact_orders", "Experience Class"), col("fact_orders", "Feedback Category"), col("fact_orders", "Sentiment")
CTYPE = col("dim_customer", "Customer Type")
CHAN, AUD, CAMP = col("fact_marketing", "Channel"), col("fact_marketing", "Target Audience"), col("fact_marketing", "Campaign Name")
FMONTH, FLABEL = col("Forecast", "Month Start"), col("Forecast", "Month Label")
LEVLAB = col("Levers", "Lever Label")
FOOTER = mea("Footer Text")
NEU = mea("Δ Neutral Color")
D = lambda m: mea(f"Δ {m}")
DC = lambda m: mea(f"Δ {m} Color")

NO_AXIS_TITLES = {"categoryAxis": [{"properties": {"showAxisTitle": L(False), "fontSize": L(9)}}],
                  "valueAxis": [{"properties": {"showAxisTitle": L(False), "gridlineShow": L(True), "fontSize": L(9)}}]}
LABELS = {"labels": [{"properties": {"show": L(True), "fontSize": L(9)}}]}
LEGEND_TOP = {"legend": [{"properties": {"show": L(True), "position": L("Top"), "fontSize": L(9)}}]}
HIDE_VALUE_AXIS = {"valueAxis": [{"properties": {"show": L(False), "showAxisTitle": L(False)}}]}
FULL = cat_filter("full_months", "Date", "Is Full Month", ["true"])           # trend visuals: full months only
ONE_COLOR = lambda c: {"dataPoint": [{"properties": {"fill": C(c)}}]}
CAT_PAD = lambda fs=9: {"categoryAxis": [{"properties": {"showAxisTitle": L(False), "fontSize": L(fs), "innerPadding": L(25)}}]}
SCALAR_X = {"categoryAxis": [{"properties": {"showAxisTitle": L(False), "fontSize": L(9), "axisType": L("Scalar")}}]}

row2_y = 190
row3_end = H - 38


def top_n_filter(name, t, c, measure, n_, descending=True):
    """Visual-level Top N filter on column t[c] by a _Measures measure."""
    sub = {"Version": 2, "From": [{"Name": "f", "Entity": t, "Type": 0}, {"Name": "m", "Entity": "_Measures", "Type": 0}],
           "Select": [{"Column": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": c}, "Name": "field"}],
           "OrderBy": [{"Direction": 2 if descending else 1,
                        "Expression": {"Measure": {"Expression": {"SourceRef": {"Source": "m"}}, "Property": measure}}}], "Top": n_}
    return {"name": name, "field": col(t, c), "type": "TopN", "howCreated": "User",
            "filter": {"Version": 2, "From": [{"Name": "subquery", "Expression": {"Subquery": {"Query": sub}}, "Type": 2}, {"Name": "f", "Entity": t, "Type": 0}],
                       "Where": [{"Condition": {"In": {"Expressions": [{"Column": {"Expression": {"SourceRef": {"Source": "f"}}, "Property": c}}],
                                                       "Table": {"SourceRef": {"Source": "subquery"}}}}}]}}


def gradient(measure, lo, hi, mid=None):
    """Matrix cell background: linear gradient on a measure (ColorBrewer ends); a mid stop is pinned at 0 for variances."""
    inp = {"Measure": {"Expression": {"SourceRef": {"Entity": "_Measures"}}, "Property": measure}}
    nul = {"nullColoringStrategy": {"strategy": {"Literal": {"Value": "'noColor'"}}}}
    stops = {"min": {"color": {"Literal": {"Value": f"'{lo}'"}}, **nul}, "max": {"color": {"Literal": {"Value": f"'{hi}'"}}}}
    kind = "linearGradient2"
    if mid:
        stops = {"min": stops["min"], "mid": {"color": {"Literal": {"Value": f"'{mid}'"}}, "value": {"Literal": {"Value": "0D"}}}, "max": stops["max"]}
        kind = "linearGradient3"
    return {"properties": {"backColor": {"solid": {"color": {"expr": {"FillRule": {"Input": inp, "FillRule": {kind: stops}}}}}}},
            "selector": {"data": [{"dataViewWildcard": {"matchingOption": 1}}], "metadata": f"_Measures.{measure}"}}


COMPACT = lambda fs=9: {"values": [{"properties": {"fontSize": L(fs)}}], "rowHeaders": [{"properties": {"fontSize": L(fs)}}],
                        "columnHeaders": [{"properties": {"fontSize": L(fs)}}], "total": [{"properties": {"show": L(False)}}],
                        "subTotals": [{"properties": {"rowSubtotals": L(False), "columnSubtotals": L(False)}}]}


def line_styles(*fields):
    """(measure, width, marker, dashed) -> per-series stroke settings."""
    out = []
    for f, w_, mk_, *dash in fields:
        props = {"strokeWidth": L(w_), "showMarker": L(mk_)}
        if dash and dash[0]:
            props["lineStyle"] = L("dashed")
        out.append({"properties": props, "selector": {"metadata": qref(f)}})
    return out


def fix_footer(pg):
    """Wider page navigator (seven tab labels) and a footer text that stops where it starts."""
    for v in pg.visuals:
        if v["name"] == "ftr_text":
            v["position"]["width"] = 560
        if v["name"] == "ftr_nav":
            v["position"]["x"], v["position"]["width"] = W - M - 680, 680


def slicer(pg, name, field, label, x, w, group=None):
    pg.slicer(name, field, label, x, w)
    if group:
        pg.visuals[-1]["visual"]["syncGroup"] = {"groupName": group, "fieldChanges": True, "filterChanges": True}


def std_slicers(pg):
    """Month, category and payment slicers at the right of the header, synced across pages 1 to 4; returns the x where they start."""
    x0 = W - M - (130 + 170 + 120 + 2 * 8)
    slicer(pg, "slc_month", YM, "Month", x0, 130, "Month")
    slicer(pg, "slc_cat", CAT, "Category", x0 + 138, 170, "Category")
    slicer(pg, "slc_pay", PAY, "Payment", x0 + 316, 120, "Payment")
    return x0


def fits(lines, w, h, pt, title_pt=12):
    """Text-fit guard for text boxes: ~0.52 em per character, 1.35 line height, 8 px between paragraphs."""
    px = pt * 1.333
    per_line = max(1, int((w - 28) / (0.52 * px)))
    used = title_pt * 1.333 * 1.5 + 10
    for ln in lines:
        txt = "".join(ln) if isinstance(ln, tuple) else ln
        used += -(-len(txt) // per_line) * px * 1.35 + 8
    assert used <= h - 10, f"text box too long: needs {used:.0f}px of {h}"


HINTS = {}   # (page, visual) -> category rows the visual must show without scrolling; written to _build/row_hints.json for check_report.py


def hint(pg, name, rows):
    HINTS[f"{pg.name}/{name}"] = rows


pages = []
# =====================================================================
# PAGE 1 - Executive overview
# =====================================================================
p = Page("overview", "1 Overview")
x0 = W - M - (130 + 170 + 120 + 2 * 8)
p.header("Overview", "Cards: selection totals  ·  change line: last full month vs the same month a year earlier",
         title_measure=mea("Title Overview"), title_w=x0 - 70)
std_slicers(p)
p.cards([
    ("card_rev", mea("Card Revenue"), "Revenue", D("Revenue"), DC("Revenue")),
    ("card_orders", mea("Card Orders"), "Orders", D("Orders"), DC("Orders")),
    ("card_aov", mea("Card AOV"), "Average order value", D("AOV"), DC("AOV")),
    ("card_ontime", mea("Card On-Time %"), "On-time orders", D("On-Time %"), DC("On-Time %")),
    ("card_rating", mea("Card Avg Rating"), "Average rating (1-5)", D("Avg Rating"), DC("Avg Rating")),
    ("card_rar", mea("Card Revenue at Risk"), "Revenue at Risk", D("Revenue at Risk"), DC("Revenue at Risk")),
])
lw, rw = 760, W - 2 * M - 760 - G
r2h = 250
r3y = row2_y + r2h + G
p.add("line_rev", "lineChart", M, row2_y, lw, r2h,
      roles={"Category": [MS], "Y": [(mea("Revenue ₹ L"), "Revenue")]},
      title=mea("Title Monthly Trend"), subtitle="₹ lakh per month  ·  Mar 2023 and Nov 2024 are partial months and are left out",
      alt="Line chart of monthly revenue in lakh rupees for the 19 full months, Apr 2023 to Oct 2024, roughly flat",
      objects={**SCALAR_X, "valueAxis": [{"properties": {"showAxisTitle": L(False), "gridlineShow": L(True), "fontSize": L(9)}}],
               "dataPoint": [{"properties": {"fill": C(GREEN)}}], "lineStyles": [{"properties": {"strokeWidth": L(3), "showMarker": L(True)}}]},
      sort=[(MS, "Ascending")], filters=[FULL])
p.add("bar_exp", "clusteredBarChart", M, r3y, lw, row3_end - r3y,
      roles={"Category": [XCLASS], "Y": [(mea("Revenue ₹ L"), "Revenue")]},
      title="Revenue by order experience, ₹ lakh", subtitle="Poor experience = late (over 5 minutes) or rated 1-2 stars; the first three bars are at risk",
      alt="Bar chart of revenue by order experience class: late and low rating, late only, low rating only, and good experience",
      objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(), **HIDE_VALUE_AXIS,
               "dataPoint": [series_color_by_value("fact_orders", "Experience Class", "Good experience", GREY),
                             series_color_by_value("fact_orders", "Experience Class", "Late and low rating", CORAL),
                             series_color_by_value("fact_orders", "Experience Class", "Late only", GOLD),
                             series_color_by_value("fact_orders", "Experience Class", "Low rating only", GOLD)]},
      sort=[(XCLASS, "Ascending")])
p.add("bar_cat", "clusteredBarChart", M + lw + G, row2_y, rw, row3_end - row2_y,
      roles={"Category": [CAT], "Y": [(mea("Line Value ₹ L"), "Line value")], "Tooltips": [(mea("Category Share"), "Share of line value"), (mea("On-Time %"), "On time"), (mea("Avg Rating"), "Avg rating")]},
      title="Line value by category, ₹ lakh", subtitle="Item lines only; hover for detail, right-click to drill through",
      alt="Sorted bar chart of line value by product category in lakh rupees, Dairy and Breakfast largest",
      objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(), **HIDE_VALUE_AXIS, **ONE_COLOR(GREEN)},
      sort=[(mea("Line Value ₹ L"), "Descending")], tooltip_page="cat_tip")
p.footer(FOOTER)
fix_footer(p)
pages.append(p)

# =====================================================================
# PAGE 2 - Sales and categories (Q1)
# =====================================================================
p = Page("sales", "2 Sales")
x0 = W - M - (130 + 170 + 120 + 2 * 8)
p.header("Sales", "Category and product visuals use line value (item lines)  ·  payment and cards use order revenue",
         title_measure=mea("Title Sales"), title_w=x0 - 70)
std_slicers(p)
p.cards([
    ("card_rev", mea("Card Revenue"), "Revenue (order total)", D("Revenue"), DC("Revenue")),
    ("card_lv", mea("Card Line Value"), "Line value (item lines)", D("Line Value"), DC("Line Value")),
    ("card_units", mea("Card Units Sold"), "Units sold", D("Units Sold"), DC("Units Sold")),
    ("card_margin", mea("Card Avg Margin %"), "Average product margin", D("Avg Margin %"), DC("Avg Margin %")),
    ("card_rpc", mea("Card Revenue per Customer"), "Revenue per customer", D("Revenue per Customer"), DC("Revenue per Customer")),
])
cw = 440
rx = M + cw + G
rwid = W - rx - M
hw = (rwid - G) // 2
p.add("bar_cat", "clusteredBarChart", M, row2_y, cw, row3_end - row2_y,
      roles={"Category": [CAT], "Y": [(mea("Line Value ₹ L"), "Line value")], "Tooltips": [(mea("Category Share"), "Share of line value"), (mea("Avg Margin %"), "Avg margin"), (mea("On-Time %"), "On time")]},
      title="Line value by category, ₹ lakh", subtitle="Right-click a category to drill through to its detail page",
      alt="Sorted bar chart of line value by category in lakh rupees; hover for share, margin and on-time rate",
      objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(), **HIDE_VALUE_AXIS, **ONE_COLOR(GREEN)},
      sort=[(mea("Line Value ₹ L"), "Descending")], tooltip_page="cat_tip")
top_h = 214
p.add("bar_prod", "clusteredBarChart", rx, row2_y, hw, top_h,
      roles={"Category": [PROD], "Y": [(mea("Line Value ₹ L"), "Line value")]},
      title="Top 5 products by line value, ₹ lakh", subtitle="Product name and id (names repeat across products)",
      alt="Sorted bar chart of the five products with the highest line value in lakh rupees",
      objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(8), **HIDE_VALUE_AXIS, **ONE_COLOR(GREEN)},
      sort=[(mea("Line Value ₹ L"), "Descending")], filters=[top_n_filter("top5_products", "dim_product", "Product Label", "Line Value", 5)])
hint(p, "bar_prod", 5)
p.add("bar_pay", "clusteredBarChart", rx + hw + G, row2_y, rwid - hw - G, top_h,
      roles={"Category": [PAY], "Y": [(mea("Revenue ₹ L"), "Revenue")]},
      title="Revenue by payment method, ₹ lakh", subtitle="Order revenue; four methods, sorted",
      alt="Sorted bar chart of order revenue in lakh rupees by payment method: card, cash, UPI and wallet",
      objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(), **HIDE_VALUE_AXIS, **ONE_COLOR(GOLD)},
      sort=[(mea("Revenue ₹ L"), "Descending")])
hint(p, "bar_pay", 4)
LAST12 = {"name": "last12", "field": MS, "type": "Advanced", "howCreated": "User",
          "filter": {"Version": 2, "From": [{"Name": "d", "Entity": "Date", "Type": 0}],
                     "Where": [{"Condition": {"Comparison": {"ComparisonKind": 2, "Left": {"Column": {"Expression": {"SourceRef": {"Source": "d"}}, "Property": "Month Start"}},
                                                             "Right": {"Literal": {"Value": "datetime'2023-11-01T00:00:00'"}}}}}]}}
heat_y = row2_y + top_h + G
p.add("mx_heat", "pivotTable", rx, heat_y, rwid, row3_end - heat_y,
      roles={"Rows": [CAT], "Columns": [YM], "Values": [(mea("Line Value ₹ L Plain"), "Line value ₹ L")]},
      title="Line value by category and month, ₹ lakh", subtitle="Last 12 full months (Nov 2023 to Oct 2024)  ·  darker green = more (ColorBrewer YlGn)",
      alt="Heat map of line value in lakh rupees by category for the last 12 full months, darker green means more",
      objects={**COMPACT(8), "grid": [{"properties": {"rowPadding": L(1)}}], "values": [{"properties": {"fontSize": L(8)}}, gradient("Line Value ₹ L Plain", th.SEQ_MIN, th.SEQ_MAX)]},
      filters=[FULL, LAST12])
hint(p, "mx_heat", 12)
p.footer(FOOTER)
fix_footer(p)
pages.append(p)

# =====================================================================
# PAGE 3 - Delivery performance (Q2)
# =====================================================================
p = Page("delivery", "3 Delivery")
x0 = W - M - (130 + 170 + 120 + 2 * 8)
p.header("Delivery", "On time = up to 5 minutes late  ·  slightly delayed 6-15  ·  significantly delayed 16-30 minutes",
         title_measure=mea("Title Delivery"), title_w=x0 - 70)
std_slicers(p)
p.cards([
    ("card_ontime", mea("Card On-Time %"), "On-time orders (target 75%)", D("On-Time %"), DC("On-Time %")),
    ("card_late", mea("Card Late %"), "Late orders", D("Late %"), DC("Late %")),
    ("card_slight", mea("Card Slightly Delayed %"), "Slightly delayed", D("Slightly Delayed %"), DC("Slightly Delayed %")),
    ("card_sig", mea("Card Significantly Delayed %"), "Significantly delayed", D("Significantly Delayed %"), DC("Significantly Delayed %")),
    ("card_min", mea("Card Avg Minutes Late"), "Minutes over the promise", D("Avg Minutes Late"), DC("Avg Minutes Late")),
])
hw = (W - 2 * M - G) // 2
r2h = 250
r3y = row2_y + r2h + G
OT, SL, SG = mea("On-Time %"), mea("Slightly Delayed %"), mea("Significantly Delayed %")
p.add("line_status", "lineChart", M, row2_y, hw, r2h,
      roles={"Category": [MS], "Y": [(OT, "On time"), (SL, "Slightly delayed"), (SG, "Significantly delayed")]},
      title="Delivery status by month, share of orders", subtitle="Full months only  ·  one scale from 0 to 100%",
      alt="Line chart of the monthly share of orders on time, slightly delayed and significantly delayed; all three are flat",
      objects={**SCALAR_X, **LEGEND_TOP, "valueAxis": [{"properties": {"showAxisTitle": L(False), "gridlineShow": L(True), "fontSize": L(9), "start": L(0), "end": L(1)}}],
               "dataPoint": [series_color_by_measure(OT, GREEN), series_color_by_measure(SL, GOLD), series_color_by_measure(SG, CORAL)],
               "lineStyles": line_styles((OT, 3, True), (SL, 3, True), (SG, 3, True))},
      sort=[(MS, "Ascending")], filters=[FULL])
p.add("col_band", "clusteredColumnChart", M + hw + G, row2_y, hw, r2h,
      roles={"Category": [BAND], "Y": [(mea("Orders"), "Orders")]},
      title="Orders by minutes late, 5-minute bands", subtitle="Source minutes late run from -5 to 30; up to 5 minutes counts as on time",
      alt="Column chart of the number of orders by minutes late in five-minute bands, from early to 26-30 minutes",
      objects={**NO_AXIS_TITLES, **LABELS, **HIDE_VALUE_AXIS, **CAT_PAD(),
               "dataPoint": [series_color_by_value("fact_orders", "Minutes Late Band", b, GREEN) for b in ("Early", "0 to 5")]
                            + [series_color_by_value("fact_orders", "Minutes Late Band", b, GOLD) for b in ("6 to 10", "11 to 15")]
                            + [series_color_by_value("fact_orders", "Minutes Late Band", b, CORAL) for b in ("16 to 20", "21 to 25", "26 to 30")]},
      sort=[(BAND, "Ascending")])
p.add("col_hour", "clusteredColumnChart", M, r3y, hw, row3_end - r3y,
      roles={"Category": [HOUR], "Y": [(mea("Late %"), "Late share")]},
      title="Late share by hour of day", subtitle="Share of orders in each hour delivered more than 5 minutes late; no peak hour",
      alt="Column chart of the late-delivery share by hour of day, 0 to 23; the share is flat around 30 percent",
      objects={**NO_AXIS_TITLES, **HIDE_VALUE_AXIS, **ONE_COLOR(GOLD),
               "labels": [{"properties": {"show": L(True), "fontSize": L(8), "labelPrecision": L(0)}}],
               "categoryAxis": [{"properties": {"showAxisTitle": L(False), "fontSize": L(8)}}]},
      sort=[(HOUR, "Ascending")])
notes3 = [("Promise kept: ", f"{ontime:.1%} of orders arrive within 5 minutes; {late_rate:.1%} are late, by {avg_late:.1f} minutes on average."),
          ("Delays are short: ", f"{slight:.0%} of orders are slightly late (6-15 minutes) and {sig:.0%} significantly (16-30)."),
          ("No peak hour: ", f"the late share stays between {hr.min():.0%} and {hr.max():.0%} in every hour."),
          ("Reasons are empty: ", f"the only delay reason is 'Traffic', also set on {on_time_traffic:,} on-time orders."),
          ("Action: ", "size the 5-point late-share lever on page 7.")]
fits(notes3, hw, row3_end - r3y, 10)
p.textbox("txt_delivery", M + hw + G, r3y, hw, row3_end - r3y, "What this tells us (all orders)", notes3)
p.footer(FOOTER)
fix_footer(p)
pages.append(p)

# =====================================================================
# PAGE 4 - Customer experience (Q2)
# =====================================================================
p = Page("experience", "4 Experience")
x0 = W - M - (130 + 170 + 120 + 2 * 8)
p.header("Experience", "Poor experience = late or rated 1-2 stars  ·  ratings 1-5  ·  sentiment comes from the feedback file",
         title_measure=mea("Title Experience"), title_w=x0 - 70)
std_slicers(p)
p.cards([
    ("card_rating", mea("Card Avg Rating"), "Average rating (1-5)", D("Avg Rating"), DC("Avg Rating")),
    ("card_low", mea("Card Low Rating %"), "Rated 1-2 stars", D("Low Rating %"), DC("Low Rating %")),
    ("card_neg", mea("Card Negative Sentiment %"), "Negative sentiment", D("Negative Sentiment %"), DC("Negative Sentiment %")),
    ("card_poor", mea("Card Poor Experience Rate"), "Poor-experience orders", D("Poor Experience Rate"), DC("Poor Experience Rate")),
    ("card_repeat", mea("Card Repeat Rate"), "Repeat customers", D("Repeat Rate"), NEU),
])
r2h = 236
r3y = row2_y + r2h + G
c3 = (W - 2 * M - 2 * G) // 3
p.add("col_rating", "clusteredColumnChart", M, row2_y, c3, r2h,
      roles={"Category": [RATING], "Y": [(mea("Orders"), "Orders")]},
      title="Orders by star rating", subtitle="1 to 5 stars; counts on the bars",
      alt="Column chart of the number of orders by star rating, 1 to 5, roughly even",
      objects={**NO_AXIS_TITLES, **LABELS, **HIDE_VALUE_AXIS, **ONE_COLOR(GREEN)}, sort=[(RATING, "Ascending")])
p.add("bar_status", "clusteredBarChart", M + c3 + G, row2_y, c3, r2h,
      roles={"Category": [STATUS], "Y": [(mea("Avg Rating"), "Average rating")], "Tooltips": [(mea("Orders"), "Orders")]},
      title="Average rating by delivery status", subtitle="Axis from 0 to 5 stars; the bars are almost equal",
      alt="Bar chart of the average rating for on-time, slightly delayed and significantly delayed orders; all close to 3.3",
      objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(), **ONE_COLOR(GREEN),
               "valueAxis": [{"properties": {"show": L(False), "showAxisTitle": L(False), "start": L(0), "end": L(5)}}]},
      sort=[(STATUS, "Ascending")])
p.add("bar_ctype", "clusteredBarChart", M + 2 * (c3 + G), row2_y, W - 2 * M - 2 * (c3 + G), r2h,
      roles={"Category": [CTYPE], "Y": [(mea("Customers Ordering"), "Customers")]},
      title="Customers by order history", subtitle="Customers with orders: one order (New) or 2+ (Repeat)",
      alt="Bar chart of ordering customers split into repeat customers and new customers with one order",
      objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(), **HIDE_VALUE_AXIS, **ONE_COLOR(GREEN)}, sort=[(mea("Customers Ordering"), "Descending")])
hw = (W - 2 * M - G) // 2
p.add("mx_sent", "pivotTable", M, r3y, hw, row3_end - r3y,
      roles={"Rows": [FBCAT], "Values": [(mea("Orders"), "Orders"), (mea("Negative Sentiment %"), "Negative share"), (mea("Negative Sentiment vs All (pp)"), "vs all orders (pp)")]},
      title="Negative sentiment by feedback category", subtitle="Colour = points above (red) or below (blue) the all-orders share; ColorBrewer RdBu",
      alt="Table of orders, negative sentiment share and difference from the overall share for each feedback category, coloured blue to red",
      objects={**COMPACT(10), "values": [{"properties": {"fontSize": L(10)}}, gradient("Negative Sentiment vs All (pp)", th.DIV_LOW, th.DIV_HIGH, th.DIV_MID)]},
      sort=[(mea("Orders"), "Descending")])
hint(p, "mx_sent", 4)
p.add("bar_rar", "clusteredBarChart", M + hw + G, r3y, hw, row3_end - r3y,
      roles={"Category": [XCLASS], "Y": [(mea("Revenue at Risk ₹ L"), "Revenue at Risk")]},
      title=mea("Title Revenue at Risk"), subtitle="Revenue of orders in each poor-experience class, ₹ lakh (good experience left out)",
      alt="Bar chart of revenue at risk in lakh rupees by experience class: late and low rating, late only, low rating only",
      objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(), **HIDE_VALUE_AXIS,
               "dataPoint": [series_color_by_value("fact_orders", "Experience Class", "Late and low rating", CORAL),
                             series_color_by_value("fact_orders", "Experience Class", "Late only", GOLD),
                             series_color_by_value("fact_orders", "Experience Class", "Low rating only", GOLD)]},
      sort=[(XCLASS, "Ascending")], filters=[cat_filter("only_poor", "fact_orders", "Experience Class", ["'Good experience'"], exclude=True)])
p.footer(FOOTER)
fix_footer(p)
pages.append(p)

# =====================================================================
# PAGE 5 - Marketing ROI (Q3)
# =====================================================================
p = Page("marketing", "5 Marketing")
x0 = W - M - (130 + 150 + 130 + 2 * 8)
p.header("Marketing", "Attributed revenue is the marketing file's own figure, not order revenue  ·  ROAS = revenue / spend",
         title_measure=mea("Title Marketing"), title_w=x0 - 70)
slicer(p, "slc_channel", CHAN, "Channel", x0, 130)
slicer(p, "slc_aud", AUD, "Audience", x0 + 138, 150)
slicer(p, "slc_month", YM, "Month", x0 + 296, 130, "Month")
p.cards([
    ("card_spend", mea("Card Marketing Spend"), "Marketing spend", D("Marketing Spend"), DC("Marketing Spend")),
    ("card_mrev", mea("Card Marketing Revenue"), "Attributed revenue", D("Marketing Revenue"), DC("Marketing Revenue")),
    ("card_roas", mea("Card ROAS"), "ROAS (target 2.0x)", D("ROAS"), DC("ROAS")),
    ("card_impr", mea("Card Impressions"), "Impressions", D("Impressions"), DC("Impressions")),
    ("card_clicks", mea("Card Clicks"), "Clicks", D("Clicks"), DC("Clicks")),
    ("card_conv", mea("Card Conversions"), "Conversions", D("Conversions"), DC("Conversions")),
])
r2h = 290
r3y = row2_y + r2h + G
c1, c2 = 400, 380
c3w = W - 2 * M - c1 - c2 - 2 * G
ROAS = mea("ROAS")
p.add("bar_channel", "clusteredBarChart", M, row2_y, c1, r2h,
      roles={"Category": [CHAN], "Y": [(ROAS, "ROAS")], "Tooltips": [(mea("Marketing Spend ₹ L"), "Spend"), (mea("CTR"), "CTR"), (mea("Conversion Rate"), "Conversion rate")]},
      title="ROAS by channel", subtitle="Revenue per ₹1 spent, from zero; hover for CTR and spend",
      alt="Sorted bar chart of ROAS by marketing channel, Email highest at about 2.05 and App lowest at about 1.92",
      objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(), **HIDE_VALUE_AXIS, **ONE_COLOR(GREEN)}, sort=[(ROAS, "Descending")], tooltip_page="chan_tip")
p.add("mx_ca", "pivotTable", M + c1 + G, row2_y, c2, r2h,
      roles={"Rows": [CHAN], "Columns": [AUD], "Values": [(ROAS, "ROAS")]},
      title="ROAS by channel and audience", subtitle="Darker = higher ROAS; All audiences is its own group",
      alt="Heat map of ROAS for each channel and target audience; all cells are between about 1.6 and 2.3",
      objects={**COMPACT(10), "values": [{"properties": {"fontSize": L(10)}}, gradient("ROAS", th.SEQ_MIN, th.SEQ_MAX)]})
p.add("bar_campaign", "clusteredBarChart", M + c1 + c2 + 2 * G, row2_y, c3w, r2h,
      roles={"Category": [CAMP], "Y": [(ROAS, "ROAS")]},
      title="ROAS by campaign, right-click to drill through", subtitle=None,
      alt="Sorted bar chart of ROAS for the nine marketing campaigns",
      objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(8), **HIDE_VALUE_AXIS, **ONE_COLOR(GREEN)}, sort=[(ROAS, "Descending")], tooltip_page="chan_tip")
hint(p, "bar_campaign", 9)
hint(p, "mx_ca", 4)
hw = (W - 2 * M - G) // 2
p.add("line_spend", "lineChart", M, r3y, hw, row3_end - r3y,
      roles={"Category": [MS], "Y": [(mea("Marketing Spend ₹ L"), "Spend")]},
      title="Marketing spend by month, ₹ lakh", subtitle="Full months only; own scale, axis not from zero (no dual axis)",
      alt="Line chart of monthly marketing spend in lakh rupees, flat at about 8 lakh",
      objects={**SCALAR_X, "valueAxis": [{"properties": {"showAxisTitle": L(False), "gridlineShow": L(True), "fontSize": L(9)}}],
               "dataPoint": [{"properties": {"fill": C(GOLD)}}], "lineStyles": [{"properties": {"strokeWidth": L(3), "showMarker": L(True)}}]},
      sort=[(MS, "Ascending")], filters=[FULL])
p.add("line_mrev", "lineChart", M + hw + G, r3y, hw, row3_end - r3y,
      roles={"Category": [MS], "Y": [(mea("Marketing Revenue ₹ L"), "Attributed revenue")]},
      title="Attributed revenue by month, ₹ lakh", subtitle="Full months only; own scale, axis not from zero",
      alt="Line chart of monthly attributed marketing revenue in lakh rupees, flat at about 16 lakh",
      objects={**SCALAR_X, "valueAxis": [{"properties": {"showAxisTitle": L(False), "gridlineShow": L(True), "fontSize": L(9)}}],
               "dataPoint": [{"properties": {"fill": C(GREEN)}}], "lineStyles": [{"properties": {"strokeWidth": L(3), "showMarker": L(True)}}]},
      sort=[(MS, "Ascending")], filters=[FULL])
p.footer(FOOTER)
fix_footer(p)
pages.append(p)

# =====================================================================
# PAGE 6 - Key insights and data notes
# =====================================================================
p = Page("insights", "6 Insights")
p.header("Insights", f"{n:,} orders, 19 full months, 11 categories, 4 channels  ·  numbers are for all data and do not follow the slicers",
         title_measure=mea("Title Insights"), title_w=1180)
gap = round(FACTS["roas_gap_ci"][0], 2), round(FACTS["roas_gap_ci"][1], 2)
finds = [
    ("1. Sales are flat. ", f"{inr(rev)} from {n:,} orders, about {FACTS['avg_orders_month']:.0f} a month; full months run {inr(fm_lo)} to {inr(fm_hi)} and Apr to Oct 2024 sits {abs(FACTS['yoy_aprOct']):.1%} below 2023."),
    ("2. Categories are evenly spread. ", f"{FACTS['top_cat']} leads with {FACTS['top_cat_share']:.1%} of line value and the top 3 hold {FACTS['top3_share']:.0%}; the smallest, {FACTS['bottom_cat']}, has {FACTS['bottom_cat_share']:.1%}."),
    ("3. One delivery in three misses the promise. ", f"{late_rate:.1%} of orders are more than 5 minutes late, by {avg_late:.1f} minutes on average; {ontime:.1%} arrive on time."),
    ("4. Late delivery does not move the rating. ", f"Late orders average {FACTS['rating_late']:.2f} stars against {FACTS['rating_ontime']:.2f} on time, yet {inr(rar)} ({rar / rev:.0%} of revenue) sits in poor-experience orders: {FACTS['late_only_share']:.0%} late only, {FACTS['low_only_share']:.0%} low rating only, {FACTS['both_share']:.0%} both."),
    ("5. Channels return almost the same. ", f"Portfolio ROAS is {mk.attributed_revenue.sum() / mk.spend.sum():.2f}x; Email {mch.roas['Email']:.2f}x to App {mch.roas['App']:.2f}x, a gap of {gap[0]:+.2f} to {gap[1]:+.2f}x (bootstrap 95%). Attributed revenue is {FACTS['mkt_to_order_rev']:.1f}x order revenue, so it cannot be tied to orders."),
    ("Do next. ", f"Cut late deliveries by 5 points first ({inr(lev['Cut late deliveries by 5 points'].annual_value)} a year of revenue no longer exposed), then test the Email shift (page 7)."),
]
notes = [
    ("Synthetic data. ", "Flat distributions, 25 feedback sentences, one item per order: read patterns as illustrations, not Blinkit's real performance."),
    ("Revenue vs line value. ", f"Revenue is the order total ({inr(rev)}). Item lines (quantity x unit price) total {inr(fo.line_value.sum())} and match the order total on 1 of 5,000 orders, so categories use line value."),
    ("Partial months. ", f"Mar 2023 ({partial['2023-03-01']} orders) and Nov 2024 ({partial['2024-11-01']} orders) are left out of trends, YoY and the forecast."),
    ("Delivery. ", "Minutes late are measured against the promise; On Time allows up to 5 minutes late; the only delay reason is Traffic."),
    ("Customers. ", "2,172 of 2,500 customers order; stored lifetime orders and registration dates are unreliable, so customer metrics come from orders."),
    ("Marketing. ", "ROAS is recomputed as revenue / spend because the stored ROAS does not match; marketing has no key to orders."),
    ("Inventory. ", "The monthly file is used (the daily file shows a 54% damage rate); there are no stock levels, so only the damage rate is reported."),
    ("Privacy and currency. ", "Name, email, phone and address were dropped before loading. Currency is assumed to be INR."),
    ("Forecast. ", f"A naive level model chosen by rolling backtest (MAPE {FACTS['backtest_mape']:.1f}%), 80% band ±{FACTS['band80'] * 100:.1f}% a month: a baseline, not a prediction."),
]
half = (W - 2 * M - G) // 2
fits(finds, half, row3_end - 80, 11)
fits(notes, half, row3_end - 80, 11)
p.textbox("txt_findings", M, 80, half, row3_end - 80, "Five findings and the next step", finds, accent=GREEN, size="11pt", gap=True)
p.textbox("txt_notes", M + half + G, 80, W - 2 * M - half - G, row3_end - 80, "Data notes and definitions", notes, accent=CORAL, size="11pt", gap=True)
p.footer(FOOTER)
fix_footer(p)
pages.append(p)

# =====================================================================
# PAGE 7 - Forecast and levers
# =====================================================================
p = Page("forecast", "7 Forecast")
p.header("Forecast", "Naive level model chosen by a rolling backtest  ·  80% band  ·  levers sized on the last 12 full months (Nov 2023 to Oct 2024)",
         title_measure=mea("Title Forecast"), title_w=1180)
p.cards([
    ("card_f25", mea("Card F25 Revenue"), "2025 revenue (forecast)", D("F25 Revenue"), DC("F25 Revenue")),
    ("card_range", mea("Card F25 Range"), "80% range for 2025", D("F25 Range"), NEU),
    ("card_vs", mea("Card F25 vs LTM"), "vs last 12 months", D("F25 vs LTM"), NEU),
    ("card_bt", mea("Card Backtest"), "Backtest error (MAPE)", D("Backtest"), NEU),
    ("card_lev", mea("Card Lever Exposure"), "Exposure removed (both cuts)", D("Lever Exposure"), NEU),
], small=("card_range", "card_vs"))
FA, FF, FL, FH = mea("Fcst Actual ₹ L"), mea("Fcst Forecast ₹ L"), mea("Fcst Low ₹ L"), mea("Fcst High ₹ L")
r2h = 226
r3y = row2_y + r2h + G
p.add("line_forecast", "lineChart", M, row2_y, W - 2 * M, r2h,
      roles={"Category": [FMONTH], "Y": [(FA, "Actual"), (FF, "Forecast"), (FL, "Low case (80%)"), (FH, "High case (80%)")]},
      title="Revenue is forecast flat at the last full month's level, ₹ lakh a month",
      subtitle="Actual Apr 2023 to Oct 2024, forecast Nov 2024 to Dec 2025, dashed lines = 80% band  ·  partial months left out",
      alt="Line chart of monthly revenue in lakh rupees: 19 actual months, then a flat forecast to December 2025 with a dashed 80 percent band",
      objects={**SCALAR_X, **LEGEND_TOP, "valueAxis": [{"properties": {"showAxisTitle": L(False), "gridlineShow": L(True), "fontSize": L(9)}}],
               "dataPoint": [series_color_by_measure(FA, GREEN), series_color_by_measure(FF, GOLD), series_color_by_measure(FL, th.BAND), series_color_by_measure(FH, th.BAND)],
               "lineStyles": line_styles((FA, 3, True), (FF, 3, True), (FL, 1, False, True), (FH, 1, False, True))},
      sort=[(FMONTH, "Ascending")])
lw = round((W - 2 * M - G) * 0.56)
p.add("bar_levers", "clusteredBarChart", M, r3y, lw, row3_end - r3y,
      roles={"Category": [LEVLAB], "Y": [(mea("Lever Value ₹ L"), "Annual value")], "Tooltips": [(mea("Lever Value % of Revenue"), "% of last-12-month revenue")]},
      title="Late deliveries and low ratings are the biggest levers", subtitle="Annual value, ₹ lakh  ·  the label names the value type (combined scenario: see card)",
      alt="Sorted bar chart of four lever values per year in lakh rupees: late deliveries, low ratings, channel shift, stock damage",
      objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(), **HIDE_VALUE_AXIS, **ONE_COLOR(GREEN)}, sort=[(mea("Lever Value ₹ L"), "Descending")],
      filters=[cat_filter("single_levers", "Levers", "Lever Type", ["'Exposure removed (combined)'"], exclude=True)])
hint(p, "bar_levers", 4)
plan = [("1. Late deliveries -5 points: ", f"{inr(lev['Cut late deliveries by 5 points'].annual_value)} of revenue no longer at risk (low confidence)."),
        ("2. Low ratings -5 points: ", f"{inr(lev['Cut 1-2 star ratings by 5 points'].annual_value)} no longer at risk (low confidence)."),
        ("3. Shift 20% of App spend to Email: ", f"{inr(lev['Move 20% of App spend to Email'].annual_value)} more attributed revenue."),
        ("4. Stock damage -0.5 points: ", f"{inr(lev['Cut stock damage by 0.5 points'].annual_value)} of stock saved at list price."),
        ("Both cuts together: ", f"{inr(lev['Cut late deliveries and low ratings by 5 points each'].annual_value)} of revenue no longer at risk, one scenario on late-or-low-rated orders (the card above); levers 1 and 2 are its parts.")
        ,("Read with care: ", "delay and rating are not linked here, exposure is not lost revenue, and the value types of levers 1-4 are not additive.")]
fits(plan, W - 2 * M - lw - G, row3_end - r3y, 10)
p.textbox("txt_plan", M + lw + G, r3y, W - 2 * M - lw - G, row3_end - r3y, "Levers and their assumptions (all data)", plan)
p.footer(FOOTER)
fix_footer(p)
pages.append(p)


# =====================================================================
# Drill-through pages (hidden): right-click a category or a campaign
# =====================================================================
def back_button(pg):
    pg.add("btn_back", "actionButton", W - M - 120, 18, 120, 36, alt="Back to the previous page",
           objects={"icon": [{"properties": {"shapeType": L("back")}, "selector": {"id": "default"}}],
                    "text": [{"properties": {"show": L(True), "text": L("Back"), "fontColor": C(WHITE)}, "selector": {"id": "default"}}]},
           container={"visualLink": [{"properties": {"show": L(True), "type": L("Back")}}], "background": [{"properties": {"show": L(False)}}],
                      "border": [{"properties": {"show": L(False)}}], "title": [{"properties": {"show": L(False)}}]})


p = Page("category_detail", "Category detail", page_type="Drillthrough", hidden=True,
         binding={"name": "category_binding", "type": "Drillthrough", "parameters": [{"name": "category_param", "boundFilter": "dt_category", "fieldExpr": CAT}]},
         filters=[{"name": "dt_category", "field": CAT, "type": "Categorical", "howCreated": "Drillthrough"}])
p.header("Category detail", "Drill-through page: one category  ·  use the Back button (Ctrl+click in Desktop) to return",
         title_measure=mea("Title Category Detail"), title_w=1000)
back_button(p)
p.cards([
    ("card_lv", mea("Card Line Value"), "Line value", D("Line Value"), DC("Line Value")),
    ("card_orders", mea("Card Orders"), "Orders", D("Orders"), DC("Orders")),
    ("card_ontime", mea("Card On-Time %"), "On-time orders", D("On-Time %"), DC("On-Time %")),
    ("card_rating", mea("Card Avg Rating"), "Average rating", D("Avg Rating"), DC("Avg Rating")),
    ("card_margin", mea("Card Avg Margin %"), "Average margin", D("Avg Margin %"), DC("Avg Margin %")),
])
hw = (W - 2 * M - G) // 2
r2h = 180
r3y = row2_y + r2h + G
p.add("col_cat_month", "clusteredColumnChart", M, row2_y, hw, r2h,
      roles={"Category": [YM], "Y": [(mea("Line Value ₹ L"), "Line value")]},
      title="Line value by month, ₹ lakh", subtitle="Full months only", alt="Column chart of the category's line value in lakh rupees by month",
      objects={**NO_AXIS_TITLES, **ONE_COLOR(GREEN)}, sort=[(YM, "Ascending")], filters=[FULL])
p.add("bar_cat_status", "clusteredBarChart", M + hw + G, row2_y, hw, r2h,
      roles={"Category": [STATUS], "Y": [(mea("Orders"), "Orders")]},
      title="Orders by delivery status", subtitle="Orders containing this category", alt="Bar chart of the category's orders by delivery status",
      objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(), **HIDE_VALUE_AXIS, **ONE_COLOR(GOLD)}, sort=[(STATUS, "Ascending")])
p.add("tbl_products", "pivotTable", M, r3y, W - 2 * M, row3_end - r3y,
      roles={"Rows": [PROD], "Values": [(mea("Line Value ₹ L"), "Line value"), (mea("Avg Margin %"), "Margin"), (mea("On-Time %"), "On time"), (mea("Avg Rating"), "Rating")]},
      title="Top 8 products in the category", subtitle="By line value", alt="Table of the category's eight top products with line value, margin, on-time rate and rating",
      objects={**COMPACT(9), "grid": [{"properties": {"rowPadding": L(1)}}]}, sort=[(mea("Line Value ₹ L"), "Descending")], filters=[top_n_filter("top8_cat_products", "dim_product", "Product Label", "Line Value", 8)])
hint(p, "tbl_products", 8)
p.footer(FOOTER, nav=False)
fix_footer(p)
pages.append(p)

p = Page("campaign_detail", "Campaign detail", page_type="Drillthrough", hidden=True,
         binding={"name": "campaign_binding", "type": "Drillthrough", "parameters": [{"name": "campaign_param", "boundFilter": "dt_campaign", "fieldExpr": CAMP}]},
         filters=[{"name": "dt_campaign", "field": CAMP, "type": "Categorical", "howCreated": "Drillthrough"}])
p.header("Campaign detail", "Drill-through page: one campaign  ·  use the Back button (Ctrl+click in Desktop) to return",
         title_measure=mea("Title Campaign Detail"), title_w=1000)
back_button(p)
p.cards([
    ("card_spend", mea("Card Marketing Spend"), "Marketing spend", D("Marketing Spend"), DC("Marketing Spend")),
    ("card_mrev", mea("Card Marketing Revenue"), "Attributed revenue", D("Marketing Revenue"), DC("Marketing Revenue")),
    ("card_roas", mea("Card ROAS"), "ROAS", D("ROAS"), DC("ROAS")),
    ("card_ctr", mea("Card CTR"), "Click-through rate", D("CTR"), DC("CTR")),
    ("card_conv", mea("Card Conversion Rate"), "Conversion rate", D("Conversion Rate"), DC("Conversion Rate")),
])
p.add("bar_camp_channel", "clusteredBarChart", M, row2_y, hw, r2h,
      roles={"Category": [CHAN], "Y": [(ROAS, "ROAS")]}, title="ROAS by channel", subtitle="This campaign only",
      alt="Bar chart of the campaign's ROAS by channel", objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(), **HIDE_VALUE_AXIS, **ONE_COLOR(GREEN)}, sort=[(ROAS, "Descending")])
p.add("bar_camp_aud", "clusteredBarChart", M + hw + G, row2_y, hw, r2h,
      roles={"Category": [AUD], "Y": [(ROAS, "ROAS")]}, title="ROAS by target audience", subtitle="This campaign only",
      alt="Bar chart of the campaign's ROAS by target audience", objects={**NO_AXIS_TITLES, **LABELS, **CAT_PAD(), **HIDE_VALUE_AXIS, **ONE_COLOR(GOLD)}, sort=[(ROAS, "Descending")])
p.add("line_camp_month", "lineChart", M, r3y, W - 2 * M, row3_end - r3y,
      roles={"Category": [MS], "Y": [(mea("Marketing Spend ₹ L"), "Spend"), (mea("Marketing Revenue ₹ L"), "Attributed revenue")]},
      title="Spend and attributed revenue by month, ₹ lakh", subtitle="Full months only; same unit and scale for both lines",
      alt="Line chart of the campaign's monthly spend and attributed revenue in lakh rupees",
      objects={**SCALAR_X, **LEGEND_TOP, "dataPoint": [series_color_by_measure(mea("Marketing Spend ₹ L"), GOLD), series_color_by_measure(mea("Marketing Revenue ₹ L"), GREEN)],
               "valueAxis": [{"properties": {"showAxisTitle": L(False), "gridlineShow": L(True), "fontSize": L(9), "start": L(0)}}],
               "lineStyles": line_styles((mea("Marketing Spend ₹ L"), 3, True), (mea("Marketing Revenue ₹ L"), 3, True))},
      sort=[(MS, "Ascending")], filters=[FULL])
p.footer(FOOTER, nav=False)
fix_footer(p)
pages.append(p)

# =====================================================================
# Tooltip pages (hover a category bar or a channel/campaign bar)
# =====================================================================
TW, TH = 400, 300


def tooltip_page(name, display, cards, line_meas, line_title, line_alt, color):
    pg = Page(name, display, page_type="Tooltip", hidden=True, binding={"name": f"{name}_binding", "type": "Tooltip"}, size=(TW, TH))
    pg.cards([(f"tip_{i}", c, lab) for i, (c, lab) in enumerate(cards)], y=6, h=64, x0=8, width=TW - 16, small=tuple(f"tip_{i}" for i in range(len(cards))))
    pg.add("tip_line", "lineChart", 8, 78, TW - 16, TH - 84, roles={"Category": [MS], "Y": [(line_meas, line_title)]},
           title=line_title, alt=line_alt, filters=[FULL],
           container={"subTitle": [{"properties": {"show": L(False)}}], "padding": [{"properties": {"top": L(4), "bottom": L(4), "left": L(6), "right": L(6)}}]},
           objects={**NO_AXIS_TITLES, "dataPoint": [{"properties": {"fill": C(color)}}], "lineStyles": [{"properties": {"strokeWidth": L(2)}}],
                    "categoryAxis": [{"properties": {"show": L(False), "axisType": L("Scalar")}}],
                    "valueAxis": [{"properties": {"start": L(0), "showAxisTitle": L(False), "fontSize": L(8)}}]},
           sort=[(MS, "Ascending")])
    for v in pg.visuals:
        if v["visual"]["visualType"] == "cardVisual":
            v["visual"]["objects"]["value"] = [{"properties": {"fontSize": L(12)}, "selector": {"id": "default"}}]
            v["visual"]["objects"]["label"] = [{"properties": {"fontSize": L(8)}, "selector": {"id": "default"}}]
    return pg


pages.append(tooltip_page("cat_tip", "Category tooltip",
                          [(mea("Card Line Value"), "Line value"), (mea("Card On-Time %"), "On time"), (mea("Card Avg Rating"), "Rating"), (mea("Card Avg Margin %"), "Margin")],
                          mea("Line Value ₹ L"), "Line value by month, ₹ lakh", "Line chart of line value in lakh rupees by month for the hovered category", GREEN))
pages.append(tooltip_page("chan_tip", "Channel tooltip",
                          [(mea("Card Marketing Spend"), "Spend"), (mea("Card ROAS"), "ROAS"), (mea("Card CTR"), "CTR"), (mea("Card Conversion Rate"), "Conversion")],
                          ROAS, "ROAS by month", "Line chart of ROAS by month for the hovered channel or campaign", GOLD))

# every visual must carry alt text (accessibility gate of the scorecard)
missing = [(pg.name, v["name"]) for pg in pages for v in pg.visuals
           if not any("altText" in x.get("properties", {}) for x in v.get("visual", {}).get("visualContainerObjects", {}).get("general", []))]
assert not missing, f"visuals without alt text: {missing}"
HINTS.update({"overview/bar_cat": 11, "overview/bar_exp": 4, "sales/bar_cat": 11, "delivery/col_band": 8, "experience/bar_status": 3,
              "experience/bar_ctype": 2, "marketing/bar_channel": 4, "experience/bar_rar": 3, "category_detail/bar_cat_status": 3,
              "campaign_detail/bar_camp_channel": 4, "campaign_detail/bar_camp_aud": 4})
(Path(__file__).parent / "row_hints.json").write_text(json.dumps(HINTS, indent=1), encoding="utf-8")
k.finish(pages)
