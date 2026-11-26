"""R1 reconcile: compute every headline number independently from data/raw, again from data/clean (CSV),
assert they are equal, write docs/reconciliation.md. Different code paths on purpose (maps/sets on raw, groupby on clean)."""
from pathlib import Path
import math
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
RAW, CLEAN, DOCS = ROOT / "data/raw", ROOT / "data/clean", ROOT / "docs"
PARTIAL = {"2023-03", "2024-11"}


def inr(x, dec=2):
    """Indian short format: Rs Cr (>= 1 crore), Rs L (>= 1 lakh), else Rs with Indian digit grouping."""
    if abs(x) >= 1e7:
        return f"₹{x / 1e7:.{dec}f} Cr"
    if abs(x) >= 1e5:
        return f"₹{x / 1e5:.{dec}f} L"
    s = f"{abs(x):.0f}"
    s = s if len(s) <= 3 else (lambda h, t: (",".join([h[max(0, i - 2):i] for i in range(len(h), 0, -2)][::-1]) + "," + t))(s[:-3], s[-3:])
    return f"₹{'-' if x < 0 else ''}{s}"


# ======================= A. from RAW (independent path)
def from_raw():
    o = pd.read_csv(RAW / "blinkit_orders.csv")
    it = pd.read_csv(RAW / "blinkit_order_items.csv")
    dl = pd.read_csv(RAW / "blinkit_delivery_performance.csv")
    fb = pd.read_csv(RAW / "blinkit_customer_feedback.csv")
    pr = pd.read_csv(RAW / "blinkit_products.csv")
    mk = pd.read_csv(RAW / "blinkit_marketing_performance.csv")
    iv = pd.read_csv(RAW / "blinkit_inventoryNew.csv")
    late_min = dict(zip(dl.order_id, dl.delivery_time_minutes))
    status = dict(zip(dl.order_id, dl.delivery_status))
    rating = dict(zip(fb.order_id, fb.rating))
    n = len(o)
    ids = o.order_id.tolist()
    mins = [late_min[i] for i in ids]
    late = [(status[i] == "Significantly Delayed") or (m > 5) for i, m in zip(ids, mins)]
    poor = [l or (rating[i] <= 2) for i, l in zip(ids, late)]
    tot = o.order_total.tolist()
    rev = sum(tot)
    poor_rev = sum(t for t, p in zip(tot, poor) if p)
    cnt = o.customer_id.value_counts()
    r = {
        "revenue": rev, "orders": n, "aov": rev / n,
        "customers_ordering": len(cnt), "repeat_rate": (cnt >= 2).sum() / len(cnt),
        "on_time_pct": sum(1 for i in ids if status[i] == "On Time") / n,
        "late_rate": sum(late) / n,
        "avg_minutes_late": sum(mins) / n,
        "avg_minutes_late_when_late": sum(m for m, l in zip(mins, late) if l) / sum(late),
        "avg_rating": sum(rating[i] for i in ids) / n,
        "poor_rate": sum(poor) / n,
        "revenue_at_risk": poor_rev,
        "revenue_at_risk_decomp": n * (sum(poor) / n) * (poor_rev / sum(poor)),  # orders x poor rate x AOV of poor orders
        "revenue_at_risk_overall_aov": n * (sum(poor) / n) * (rev / n),
        "revenue_at_risk_share": poor_rev / rev,
    }
    # category by LINE value (quantity x unit_price), not order_total
    cat = dict(zip(pr.product_id, pr.category))
    lv = {}
    for pid, q, p in zip(it.product_id, it.quantity, it.unit_price):
        lv[cat[pid]] = lv.get(cat[pid], 0) + q * p
    r["line_value_total"] = sum(lv.values())
    for k, v in lv.items():
        r[f"line_value|{k}"] = v
    # monthly revenue, full months only
    mrev = {}
    for d, t in zip(o.order_date, o.order_total):
        mrev[d[:7]] = mrev.get(d[:7], 0) + t
    mrev = {k: v for k, v in mrev.items() if k not in PARTIAL}
    r["full_months"] = len(mrev)
    for k, v in mrev.items():
        r[f"month|{k}"] = v
        py = f"{int(k[:4]) - 1}{k[4:]}"
        if py in mrev:
            r[f"yoy|{k}"] = v / mrev[py] - 1
    # marketing
    for ch, g in mk.groupby("channel"):
        r[f"mkt_spend|{ch}"] = g.spend.sum()
        r[f"mkt_revenue|{ch}"] = g.revenue_generated.sum()
        r[f"mkt_roas|{ch}"] = g.revenue_generated.sum() / g.spend.sum()
    r["mkt_spend"], r["mkt_revenue"] = mk.spend.sum(), mk.revenue_generated.sum()
    r["mkt_roas"] = mk.revenue_generated.sum() / mk.spend.sum()
    r["damage_rate"] = iv.damaged_stock.sum() / iv.stock_received.sum()
    return r


# ======================= B. from CLEAN (CSV that Power Query will load)
def from_clean():
    fo = pd.read_csv(CLEAN / "fact_orders.csv", parse_dates=["order_date"])
    fm = pd.read_csv(CLEAN / "fact_marketing.csv")
    fi = pd.read_csv(CLEAN / "fact_inventory.csv")
    dp = pd.read_csv(CLEAN / "dim_product.csv")
    dc = pd.read_csv(CLEAN / "dim_customer.csv")
    n, rev = len(fo), fo.order_total.sum()
    ordering = dc[dc.orders > 0]
    poor = fo[fo.poor_experience]
    r = {
        "revenue": rev, "orders": n, "aov": fo.order_total.mean(),
        "customers_ordering": len(ordering), "repeat_rate": (ordering.customer_type == "Repeat").mean(),
        "on_time_pct": (fo.delivery_status == "On Time").mean(),
        "late_rate": fo.is_late.mean(),
        "avg_minutes_late": fo.minutes_late.mean(),
        "avg_minutes_late_when_late": fo.loc[fo.is_late, "minutes_late"].mean(),
        "avg_rating": fo.rating.mean(),
        "poor_rate": fo.poor_experience.mean(),
        "revenue_at_risk": poor.order_total.sum(),
        "revenue_at_risk_decomp": n * fo.poor_experience.mean() * poor.order_total.mean(),
        "revenue_at_risk_overall_aov": n * fo.poor_experience.mean() * fo.order_total.mean(),
        "revenue_at_risk_share": poor.order_total.sum() / fo.order_total.sum(),
    }
    lv = fo.merge(dp[["product_id", "category"]], on="product_id").groupby("category").line_value.sum()
    r["line_value_total"] = lv.sum()
    for k, v in lv.items():
        r[f"line_value|{k}"] = v
    full = fo[fo.is_full_month].groupby(fo.order_date.dt.strftime("%Y-%m")).order_total.sum()
    r["full_months"] = len(full)
    for k, v in full.items():
        r[f"month|{k}"] = v
        py = f"{int(k[:4]) - 1}{k[4:]}"
        if py in full.index:
            r[f"yoy|{k}"] = v / full[py] - 1
    by = fm.groupby("channel")[["spend", "attributed_revenue"]].sum()
    for ch, row in by.iterrows():
        r[f"mkt_spend|{ch}"], r[f"mkt_revenue|{ch}"] = row.spend, row.attributed_revenue
        r[f"mkt_roas|{ch}"] = row.attributed_revenue / row.spend
    r["mkt_spend"], r["mkt_revenue"] = fm.spend.sum(), fm.attributed_revenue.sum()
    r["mkt_roas"] = r["mkt_revenue"] / r["mkt_spend"]
    r["damage_rate"] = fi.damaged_stock.sum() / fi.stock_received.sum()
    return r


a, b = from_raw(), from_clean()
assert a.keys() == b.keys(), set(a) ^ set(b)
bad = {k: (a[k], b[k]) for k in a if not math.isclose(a[k], b[k], rel_tol=1e-9, abs_tol=1e-6)}
assert not bad, bad
assert math.isclose(a["revenue_at_risk"], a["revenue_at_risk_decomp"], rel_tol=1e-9)
assert abs(a["revenue_at_risk_share"] - 0.458) < 0.001           # page 4 title: share of TOTAL revenue (45.8%), not of poor orders
assert a["orders"] == 5000 and a["customers_ordering"] == 2172 and a["full_months"] == 19
assert math.isclose(a["revenue"], 11009308, abs_tol=1)           # audit: order_total sum 11.01M
assert abs(a["line_value_total"] - 4.97e6) < 5e4                 # audit: item lines 4.97M
assert abs(a["mkt_roas"] - 1.97) < 0.005                         # audit: portfolio ROAS 1.97
assert abs(a["damage_rate"] - 0.0385) < 0.0005                   # audit: inventoryNew 3.85%

# ======================= C. forecast and levers (data/clean/forecast.csv, levers.csv from _build/forecast.py), recomputed with plain Python loops
import csv
import json


def rows(name):
    with open(CLEAN / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


facts = json.loads((CLEAN / "report_facts.json").read_text(encoding="utf-8"))
fc, lv = rows("forecast.csv"), rows("levers.csv")
act = [r for r in fc if r["kind"] == "Actual"]
assert len(act) == 19 and all(math.isclose(float(r["actual"]), a[f"month|{r['month_start'][:7]}"], abs_tol=0.01) for r in act), "forecast actuals differ from monthly revenue"
ym = [float(r["actual"]) for r in act]
# rolling-origin backtest of the naive (last full month) model, written out independently: train on 10..13 months, forecast 6 ahead
errs = [abs(ym[i + j] - ym[i - 1]) / ym[i + j] for i in range(10, len(ym) - 6 + 1) for j in range(6)]
c_mape = sum(errs) / len(errs) * 100
assert facts["backtest_best"].startswith("Naive") and math.isclose(c_mape, facts["backtest_mape"], abs_tol=0.006), (c_mape, facts["backtest_mape"])
fut = [r for r in fc if r["kind"] == "Forecast"]
assert len(fut) == 14 and all(math.isclose(float(r["forecast"]), ym[-1], abs_tol=0.01) for r in fut), "naive forecast must equal the last full month"
f25 = sum(float(r["forecast"]) for r in fut if r["month_start"].startswith("2025"))
assert math.isclose(f25, 12 * ym[-1], rel_tol=1e-9) and math.isclose(f25, facts["f25"], abs_tol=0.5)
ltm = sum(ym[-12:])
assert math.isclose(ltm, facts["ltm_revenue"], abs_tol=0.5)
# levers 1 and 2 from the order rows (last 12 full months = Nov 2023 to Oct 2024)
ordr = [r for r in rows("fact_orders.csv") if "2023-11-01" <= r["month_start"] <= "2024-10-01"]
n12 = len(ordr)
late = [r["is_late"] == "True" for r in ordr]
l1 = 0.05 / (sum(late) / n12) * sum(float(r["order_total"]) for r, lt in zip(ordr, late) if lt and int(r["rating"]) > 2)
lowr = [int(r["rating"]) <= 2 for r in ordr]
l2 = 0.05 / (sum(lowr) / n12) * sum(float(r["order_total"]) for r, lt, lo in zip(ordr, late, lowr) if lo and not lt)
# combined scenario: late-only x f1 + low-only x f2 + both x f1 x f2 (no double counting)
f1, f2 = 0.05 / (sum(late) / n12), 0.05 / (sum(lowr) / n12)
only_l = sum(float(r["order_total"]) for r, lt, lo in zip(ordr, late, lowr) if lt and not lo)
only_o = sum(float(r["order_total"]) for r, lt, lo in zip(ordr, late, lowr) if lo and not lt)
both_ = sum(float(r["order_total"]) for r, lt, lo in zip(ordr, late, lowr) if lo and lt)
l2b = f1 * only_l + f2 * only_o + f1 * f2 * both_
got = {r["lever"]: float(r["annual_value"]) for r in lv}
assert math.isclose(got["Cut late deliveries and low ratings by 5 points each"], l2b, abs_tol=0.01), (got, l2b)
assert math.isclose(got["Cut late deliveries by 5 points"], l1, abs_tol=0.01) and math.isclose(got["Cut 1-2 star ratings by 5 points"], l2, abs_tol=0.01)
# lever 3: 20% of the lowest-ROAS channel's last-12-month spend moved to the highest-ROAS channel (full-period ROAS)
mk12 = [r for r in rows("fact_marketing.csv") if "2023-11-01" <= r["month_start"] <= "2024-10-01"]
chs = [k.split("|")[1] for k in a if k.startswith("mkt_roas|")]
lo_ch, hi_ch = min(chs, key=lambda c: a[f"mkt_roas|{c}"]), max(chs, key=lambda c: a[f"mkt_roas|{c}"])
l3 = 0.20 * sum(float(r["spend"]) for r in mk12 if r["channel"] == lo_ch) * (a[f"mkt_roas|{hi_ch}"] - a[f"mkt_roas|{lo_ch}"])
assert math.isclose(got[f"Move 20% of {lo_ch} spend to {hi_ch}"], l3, abs_tol=0.01), (got, l3)
# lever 4: 0.5 point of units received in the last 12 months, valued at the received-weighted list price
price = {r["product_id"]: float(r["price"]) for r in rows("dim_product.csv")}
inv12 = [r for r in rows("fact_inventory.csv") if "2023-11-01" <= r["month_start"] <= "2024-10-01"]
l4 = 0.005 * sum(int(r["stock_received"]) * price[r["product_id"]] for r in inv12)
assert math.isclose(got["Cut stock damage by 0.5 points"], l4, abs_tol=0.01)
print(f"forecast + levers OK: MAPE {c_mape:.2f}%, 2025 {inr(f25)}, levers {inr(l1)} / {inr(l2)} / {inr(l3)} / {inr(l4)}")

# ======================= write docs/reconciliation.md
pc = lambda x, d=1: f"{x * 100:.{d}f}%"
L = ["# Reconciliation (generated by `_build/reconcile.py`)\n",
     "Every number below was computed from `data/raw` (plain Python) and again from `data/clean` (pandas); all "
     f"{len(a)} values are equal (rel. tolerance 1e-9). Report cards and DAX titles must match this file. Amounts in assumed INR.\n",
     "## Headline numbers\n", "| # | Measure | Value | Definition |", "|---|---|---|---|"]
H = [
 ("Revenue", inr(a["revenue"]) + f" ({a['revenue']:,.2f})", "SUM(order_total)"),
 ("Orders", f"{a['orders']:,}", "COUNTROWS(fact_orders)"),
 ("Average order value", f"₹{a['aov']:,.2f}", "Revenue / Orders"),
 ("Customers ordering", f"{a['customers_ordering']:,}", "DISTINCTCOUNT(customer_id) in orders (customers.csv has 2,500)"),
 ("Repeat rate", pc(a["repeat_rate"]), "customers with 2+ orders / customers ordering"),
 ("On-time %", pc(a["on_time_pct"]), "delivery_status = On Time (includes up to 5 min late); late % = " + pc(a["late_rate"])),
 ("Avg minutes late", f"{a['avg_minutes_late']:.2f}", f"mean of minutes_late, early counts negative; {a['avg_minutes_late_when_late']:.2f} among late orders"),
 ("Avg rating", f"{a['avg_rating']:.2f}", "mean rating 1-5"),
 ("Poor-experience rate", pc(a["poor_rate"]), "late OR rating <= 2"),
 ("Revenue at Risk", inr(a["revenue_at_risk"]) + f" ({a['revenue_at_risk']:,.2f})",
  f"revenue of poor-experience orders = orders x poor rate x AOV of those orders; with overall AOV: {inr(a['revenue_at_risk_overall_aov'])}"),
 ("Revenue at Risk share", pc(a["revenue_at_risk_share"]), "Revenue at Risk / total revenue (the page 4 title uses this, with the class filter removed)"),
]
L += [f"| {i} | {m} | {v} | {d} |" for i, (m, v, d) in enumerate(H, 1)]
L += ["", "## Category mix by LINE value (quantity x unit_price, not order revenue)\n",
      f"Line value total {inr(a['line_value_total'])} versus order revenue {inr(a['revenue'])}: the two do not reconcile in the source "
      "(order_total matches quantity x unit_price on 1 of 5,000 orders), so categories show line value and the page says so.\n",
      "| Category | Line value | Share |", "|---|---|---|"]
cats = sorted(((k.split("|")[1], v) for k, v in a.items() if k.startswith("line_value|")), key=lambda x: -x[1])
L += [f"| {c} | {inr(v)} ({v:,.0f}) | {pc(v / a['line_value_total'])} |" for c, v in cats]
L += ["", "## Monthly revenue, full months only (Mar 2023 and Nov 2024 excluded)\n",
      "YoY only where the same month exists in both years (Apr to Oct); Jan to Mar 2024 have no 2023 comparison.\n",
      "| Month | Revenue | YoY |", "|---|---|---|"]
for k in sorted(k for k in a if k.startswith("month|")):
    m = k.split("|")[1]
    y = a.get(f"yoy|{m}")
    L.append(f"| {m} | {inr(a[k])} ({a[k]:,.0f}) | {'n/a' if y is None else f'{y * 100:+.1f}%'} |")
L += ["", "## Marketing by channel (attributed revenue, not order revenue; ROAS = revenue / spend)\n",
      "| Channel | Spend | Attributed revenue | ROAS |", "|---|---|---|---|"]
for ch in sorted(k.split("|")[1] for k in a if k.startswith("mkt_spend|")):
    L.append(f"| {ch} | {inr(a['mkt_spend|' + ch])} | {inr(a['mkt_revenue|' + ch])} | {a['mkt_roas|' + ch]:.2f} |")
L.append(f"| **All** | {inr(a['mkt_spend'])} | {inr(a['mkt_revenue'])} | {a['mkt_roas']:.2f} |")
L += ["", f"## Inventory damage rate\n", f"damaged / received (inventoryNew, product x month) = {pc(a['damage_rate'], 2)}\n"]
L += ["", "## Forecast and levers (re-derived with plain Python loops from data/clean; `_build/forecast.py` output must match)\n",
      f"Naive (last full month) model, rolling-origin backtest (train 10 to 13 months, forecast 6): MAPE {c_mape:.2f}%. "
      f"Forecast = {inr(ym[-1])} a month for Nov 2024 to Dec 2025; 2025 total {inr(f25)}; last 12 full months {inr(ltm)} ({f25 / ltm - 1:+.1%}).\n",
      "| Lever (basis Nov 2023 to Oct 2024) | Annual value |", "|---|---|",
      f"| Cut late deliveries by 5 points | {inr(l1)} ({l1:,.0f}) |", f"| Cut 1-2 star ratings by 5 points | {inr(l2)} ({l2:,.0f}) |",
      f"| Cut late deliveries and low ratings by 5 points each (one scenario, not l1 + l2) | {inr(l2b)} ({l2b:,.0f}) |",
      f"| Move 20% of {lo_ch} spend to {hi_ch} | {inr(l3)} ({l3:,.0f}) |", f"| Cut stock damage by 0.5 points | {inr(l4)} ({l4:,.0f}) |", ""]
(DOCS / "reconciliation.md").write_text("\n".join(L), encoding="utf-8")
print(f"reconcile OK: {len(a)} values match")
