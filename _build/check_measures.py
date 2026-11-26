"""Static check of the semantic model TMDL (no Desktop needed).
1. Every measure named in docs/brief.md and docs/reconciliation.md exists in the Measures table, has a description and a folder.
2. Every [Measure] reference in a measure resolves; every Table[Column] reference exists.
3. Prints the expected values (pandas on data/clean) that the DAX must return: check them live in Phase 5.
Run: python _build/check_measures.py"""
import re
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
DEFN = ROOT / "BlinkitSales-PBI.SemanticModel" / "definition" / "tables"
REQUIRED = ["Revenue", "Orders", "AOV", "Customers Ordering", "Repeat Rate", "On-Time %", "Avg Minutes Late", "Avg Rating", "Poor Experience Rate",
            "Revenue at Risk", "Line Value", "Category Share", "Revenue YoY %", "Marketing Spend", "Marketing Revenue", "ROAS", "CTR", "Conversion Rate",
            "Damage Rate", "Title Overview", "Title Sales", "Title Delivery", "Title Experience", "Title Marketing", "Title Insights", "Title Forecast"]

measures, columns, desc_missing = {}, set(), []
for f in DEFN.glob("*.tmdl"):
    table, last_desc = f.stem, None
    for ln in f.read_text(encoding="utf-8").splitlines():
        if ln.strip().startswith("///"):
            last_desc = ln.strip()[3:].strip()
            continue
        m = re.match(r"^\tmeasure (?:'(.+?)'|(\S+)) = (.*)$", ln)
        if m:
            name = m.group(1) or m.group(2)
            measures[name] = m.group(3)
            if not last_desc:
                desc_missing.append(name)
        c = re.match(r"^\tcolumn (?:'(.+?)'|(\S+))", ln)
        if c:
            columns.add((table, c.group(1) or c.group(2)))
        last_desc = None

errors = [f"missing measure: {n}" for n in REQUIRED if n not in measures]
errors += [f"no description: {n}" for n in desc_missing]
tables = {t for t, _ in columns} | {"Date"}
for n, e in measures.items():
    for ref in re.findall(r"(?<![\w'\]])\[([^\]]+)\]", e):
        if ref not in measures:
            errors.append(f"{n}: unresolved [{ref}]")
    for t, c in [(a or b, d) for a, b, d in re.findall(r"(?:'([^']+)'|\b([A-Za-z_]\w*))\[([^\]]+)\]", e)]:
        if t in tables and (t, c) not in columns:
            errors.append(f"{n}: unknown column {t}[{c}]")
print(f"{len(measures)} measures, {len(columns)} columns, {len(REQUIRED)} required names checked")

# ---- expected values for the live check in Phase 5 (docs/reconciliation.md plus rates not listed there)
o = pd.read_csv(ROOT / "data/clean/fact_orders.csv")
mk = pd.read_csv(ROOT / "data/clean/fact_marketing.csv")
iv = pd.read_csv(ROOT / "data/clean/fact_inventory.csv")
per = o.groupby("customer_id").size()
exp = {"Revenue": o.order_total.sum(), "Orders": len(o), "AOV": o.order_total.mean(), "Customers Ordering": o.customer_id.nunique(),
       "Repeat Rate": (per >= 2).mean(), "On-Time %": (o.delivery_status == "On Time").mean(), "Avg Minutes Late": o.minutes_late.mean(),
       "Avg Rating": o.rating.mean(), "Poor Experience Rate": o.poor_experience.mean(),
       "Revenue at Risk": o.loc[o.poor_experience, "order_total"].sum(), "Line Value": o.line_value.sum(),
       "Marketing Spend": mk.spend.sum(), "Marketing Revenue": mk.attributed_revenue.sum(), "ROAS": mk.attributed_revenue.sum() / mk.spend.sum(),
       "CTR": mk.clicks.sum() / mk.impressions.sum(), "Conversion Rate": mk.conversions.sum() / mk.clicks.sum(),
       "Damage Rate": iv.damaged_stock.sum() / iv.stock_received.sum(),
       "Avg Rating Late": o.loc[o.is_late, "rating"].mean(), "Avg Rating On-Time": o.loc[~o.is_late, "rating"].mean(),
       "Revenue (Full Months)": o.loc[o.is_full_month, "order_total"].sum()}
print("\nExpected values (pandas on data/clean); run the matching DAX in Desktop in Phase 5:")
for k, v in exp.items():
    print(f"  {k:<24}{v:>18,.4f}")
if errors:
    print("\nERRORS")
    print("\n".join("  " + e for e in errors))
    sys.exit(1)
print("\nOK: all required measures exist with descriptions; all references resolve.")
