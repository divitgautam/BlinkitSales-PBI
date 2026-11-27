# %% [markdown]
# # 00 · Load and clean
# Re-runs the cleaning step (`_build/prepare.py`, which drops customer name, email, phone and address on load), proves the
# clean tables did not change, asserts every table count and checks the headline numbers against `docs/reconciliation.md`.
# Every later notebook starts from `data/clean/*.parquet`.
# %%
import sys, hashlib, io, runpy, contextlib
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from IPython.display import display
from viz_style import *
from data_io import *
pd.set_option("display.width", 160); pd.set_option("display.max_columns", 40)
# %% [markdown]
# ## Run the cleaning logic and check it is reproducible
# %%
def digest():
    return {p.name: hashlib.sha256(p.read_bytes()).hexdigest()[:12] for p in sorted(CLEAN.glob("*.csv")) if p.name.startswith(("fact_", "dim_"))}
before = digest()
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    runpy.run_path(str(ROOT / "_build/prepare.py"), run_name="__main__")
print(buf.getvalue().strip())
after = digest()
assert before == after, "clean tables changed after re-running prepare.py"
print("clean CSVs identical after re-run:", len(after), "files")
# %% [markdown]
# ## Table shapes and counts
# %%
T = {n: clean(n) for n in ["fact_orders", "fact_marketing", "fact_inventory", "dim_product", "dim_customer"]}
EXPECT = {"fact_orders": 5000, "fact_marketing": 5400, "fact_inventory": 18105 - 7359 - 0, "dim_product": 268, "dim_customer": 2500}
shapes = pd.DataFrame({n: {"rows": len(t), "columns": t.shape[1], "key unique": (t.iloc[:, 0].is_unique if n != "fact_inventory" else not t.duplicated(["product_id", "month_start"]).any())} for n, t in T.items()}).T
display(shapes)
assert len(T["fact_orders"]) == 5000 and T["fact_orders"].order_id.is_unique
assert len(T["fact_marketing"]) == 5400 and len(T["dim_product"]) == 268 and len(T["dim_customer"]) == 2500
assert T["fact_inventory"].stock_received.sum() == raw("inventoryNew").stock_received.sum()
assert (T["dim_customer"].orders > 0).sum() == 2172 and T["dim_customer"].orders.sum() == 5000
print("raw -> clean row counts: orders 5,000 | marketing 5,400 | inventoryNew 18,105 -> product x month", len(T["fact_inventory"]))
# %% [markdown]
# ## Privacy check
# No personal column exists in any clean table, and the raw loader used by the notebooks filters them on read.
# %%
leak = {n: sorted(PII & set(t.columns)) for n, t in T.items()}
assert not any(leak.values()), leak
assert not (PII & set(raw("customers").columns))
print("personal columns in clean tables: none; raw loader drops", sorted(PII))
# %% [markdown]
# ## Headline numbers vs `docs/reconciliation.md`
# %%
o = orders_enriched()
H = headline_numbers(o, T["fact_marketing"], T["fact_inventory"].merge(T["dim_product"][["product_id"]], on="product_id"))
REF = {"revenue": 11009308.50, "orders": 5000, "aov": 2201.86, "customers_ordering": 2172, "repeat_rate": .687, "on_time": .694, "avg_minutes_late": 4.44,
       "avg_rating": 3.34, "poor_rate": .458, "rar": 5042193.50, "rar_share": .458, "roas": 1.97, "damage_rate": .0385}
TOL = {"revenue": .005, "aov": .005, "avg_minutes_late": .005, "avg_rating": .005, "rar": .005, "roas": .005}
rows = []
for k, ref in REF.items():
    tol = TOL.get(k, .0005 if ref < 1 else 0)
    ok = abs(H[k] - ref) <= tol + 1e-9
    rows.append((k, H[k], ref, "OK" if ok else "MISMATCH"))
    assert ok, (k, H[k], ref)
display(pd.DataFrame(rows, columns=["measure", "recomputed", "reconciliation.md", "check"]).style.format({"recomputed": "{:,.4f}", "reconciliation.md": "{:,.4f}"}))
for ch, ref in {"App": 1.92, "Email": 2.05, "SMS": 1.99, "Social Media": 1.94}.items():
    assert round(H["roas_channel"][ch], 2) == ref, ch
print("channel ROAS match:", {k: round(v, 2) for k, v in H["roas_channel"].items()})
