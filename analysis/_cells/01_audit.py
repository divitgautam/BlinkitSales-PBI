# %% [markdown]
# # 01 · Data audit in charts
# Five pictures of the quality problems found in `docs/audit.md`: nulls, duplicates and orphan keys; order total vs item lines;
# orders before registration; stored vs recomputed ROAS; and the two inventory files. Raw files are read without personal columns.
# %%
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from IPython.display import display
from viz_style import *
from data_io import *
# %% [markdown]
# ## 1. Null / duplicate / orphan matrix
# %%
R = {n: raw(n) for n in ["orders", "order_items", "products", "customers", "delivery_performance", "customer_feedback", "marketing_performance", "inventory", "inventoryNew"]}
KEY = {"orders": ["order_id"], "order_items": ["order_id", "product_id"], "products": ["product_id"], "customers": ["customer_id"],
       "delivery_performance": ["order_id"], "customer_feedback": ["feedback_id"], "marketing_performance": ["campaign_id"],
       "inventory": ["product_id", "date"], "inventoryNew": ["product_id", "date"]}
# child key -> parent table (orphans of the child, and parents without any child row)
LINK = {"orders": ("customer_id", "customers"), "order_items": ("order_id", "orders"), "delivery_performance": ("order_id", "orders"),
        "customer_feedback": ("order_id", "orders"), "inventory": ("product_id", "products"), "inventoryNew": ("product_id", "products")}
rows = []
for n, t in R.items():
    dup_key = int(t.duplicated(KEY[n]).sum())
    orphan_child = 0
    if n in LINK:
        col, par = LINK[n]
        orphan_child = int((~t[col].isin(R[par][col])).sum())
    parents_wo_child = 0
    for c, (col, par) in LINK.items():
        if par == n:
            parents_wo_child = max(parents_wo_child, int((~R[n][col].isin(R[c][col])).sum()))
    rows.append({"table": n.replace("_performance", "").replace("customer_", ""), "rows": len(t), "null cells": int(t.isna().sum().sum()),
                 "duplicate rows": int(t.duplicated().sum()), "duplicate keys": dup_key, "orphan child keys": orphan_child,
                 "parents without rows": parents_wo_child})
Q = pd.DataFrame(rows).set_index("table")
display(Q)
assert Q.loc["orders", "rows"] == 5000 and Q.loc["inventoryNew", "duplicate keys"] == 12534 and Q.loc["customers", "parents without rows"] == 328
assert Q.loc["delivery", "null cells"] == 1902
# %%
fig, ax = new_fig(h=4.8, left=0.16)
issue = Q.drop(columns="rows")
flag = (issue > 0).astype(int)
sns.heatmap(flag, ax=ax, cmap=ListedColormap([LTGREEN, YELLOW]), cbar=False, linewidths=2, linecolor="white", vmin=0, vmax=1,
            annot=issue.map(lambda v: "0" if v == 0 else f"{v:,}"), fmt="", annot_kws={"fontsize": 10, "color": INK})
ax.set_xlabel(""); ax.set_ylabel(""); ax.tick_params(length=0, labelsize=9); ax.xaxis.tick_top()
ax.set_yticks(np.arange(len(Q)) + .5, [f"{n}  ({r:,})" for n, r in zip(Q.index, Q.rows)], rotation=0)
headline(fig, "Keys are clean except in the monthly inventory file; 328 customers never ordered",
         "Count of problems per source table (green = none, yellow = found). Row count in brackets.")
footnote(fig, "Source: data/raw (Kaggle akxiit/blinkit-sales-dataset), same checks as _build/audit.py. Null cells are only the 'reasons_if_delayed' blanks. "
              "inventoryNew repeats product x month up to six times and is summed in the clean layer.")
print(save(fig, "eda/01_audit_quality_matrix"))
# %% [markdown]
# ## 2. Order total vs item-line value
# %%
o = orders_enriched()
r = o.order_total.corr(o.line_value); match = int((np.isclose(o.order_total, o.line_value, atol=0.01)).sum())
print("corr", round(r, 3), "| equal on", match, "orders | totals", round(o.order_total.sum()), round(o.line_value.sum()))
fig, ax = new_fig(h=4.8)
ax.scatter(o.line_value, o.order_total, s=7, alpha=.35, color=GREEN, linewidths=0)
m = max(o.line_value.max(), o.order_total.max())
ax.plot([0, m], [0, m], color=INK, lw=1, ls="--")
ax.text(m * .5, m * .53, "line value = order total", fontsize=8.5, rotation=28, color=INK)
ax.set_xlim(0, o.line_value.max() * 1.03); ax.set_ylim(0, m * 1.03)
ax.set_xlabel("Item line value (quantity x unit price), ₹"); ax.set_ylabel("Order total, ₹"); clean_axes(ax, "both")
note(ax, .98, .05, f"r = {r:.2f} on 5,000 orders\nmatches on {match} of 5,000\nline value ₹{o.line_value.sum() / 1e5:.1f} L vs order total ₹{o.order_total.sum() / 1e5:.1f} L",
     transform=ax.transAxes, ha="right", va="bottom", fontsize=9.5, bbox=dict(fc="white", ec=LTGREY, boxstyle="round,pad=.4"))
headline(fig, "Order total and item-line value are unrelated, so revenue and category mix cannot be reconciled",
         "Each dot is one order; points on the dashed line would reconcile")
footnote(fig, "Source: data/clean fact_orders. Decision: revenue = order_total; categories are shown by 'line value' and never mixed with revenue on one visual.")
print(save(fig, "eda/02_order_total_vs_line_value"))
# %% [markdown]
# ## 3. Orders before the customer's registration date
# %%
gap = (o.order_date - o.registration_date).dt.days
share = (gap < 0).mean()
print("orders before registration:", int((gap < 0).sum()), round(share, 3))
fig, ax = new_fig(h=4.6)
bins = np.arange(-600, 601, 30)
ax.hist(gap[gap >= 0], bins=bins, color=GREEN, label="after registration")
ax.hist(gap[gap < 0], bins=bins, color=YELLOW, label="before registration")
ax.axvline(0, color=INK, lw=1)
ax.set_xlabel("Order date minus registration date, days"); ax.set_ylabel("Orders"); clean_axes(ax)
ax.legend(loc="upper left")
note(ax, .02, .72, f"{share:.0%} of orders ({int((gap < 0).sum()):,}) precede the\ncustomer's registration date", transform=ax.transAxes, fontsize=10)
headline(fig, f"{share:.0%} of orders were placed before the customer registered, so registration date is not usable for cohorts",
         "Orders by days from registration; 30-day bins")
footnote(fig, "Source: data/clean fact_orders and dim_customer. Acquisition cohorts therefore use the first order month, not the registration date.")
print(save(fig, "eda/03_orders_before_registration"))
# %% [markdown]
# ## 4. Stored vs recomputed ROAS
# %%
mk = R["marketing_performance"]
mk["roas_calc"] = mk.revenue_generated / mk.spend
match = int(np.isclose(mk.roas, mk.roas_calc, atol=0.01).sum())
print("ROAS stored==recomputed on", match, "of", len(mk), "| mean stored", round(mk.roas.mean(), 2), "| portfolio", round(mk.revenue_generated.sum() / mk.spend.sum(), 2))
assert match == 26
fig, (a1, a2) = new_fig(h=4.6, ncols=2)
a1.scatter(mk.roas_calc, mk.roas, s=6, alpha=.3, color=GREEN, linewidths=0)
a1.plot([0, 9], [0, 9], color=INK, ls="--", lw=1)
a1.set_xlim(0, 9); a1.set_ylim(1, 4.5); a1.set_xlabel("ROAS recomputed (revenue / spend)"); a1.set_ylabel("ROAS stored in the file"); clean_axes(a1, "both")
note(a1, .97, .05, f"equal on {match} of {len(mk):,} rows", transform=a1.transAxes, ha="right", fontsize=9.5)
a1.set_title("Stored ROAS is a separate random draw (1.5 to 4)")
a2.hist(mk.roas_calc, bins=np.arange(0, 10.1, .25), color=GREEN, alpha=.85, label=f"recomputed (portfolio {mk.revenue_generated.sum() / mk.spend.sum():.2f})")
a2.hist(mk.roas, bins=np.arange(0, 10.1, .25), color=YELLOW, alpha=.9, label=f"stored (mean {mk.roas.mean():.2f})")
a2.set_xlabel("ROAS per row"); a2.set_ylabel("Rows"); clean_axes(a2); a2.legend(); a2.set_title("Distributions differ")
headline(fig, f"The stored ROAS does not equal revenue / spend; the report recomputes it as SUM / SUM (1.97, not {mk.roas.mean():.2f})",
         "5,400 campaign rows")
footnote(fig, "Source: data/raw marketing_performance. Aggregate ROAS is always total attributed revenue / total spend, never the mean of row ratios.")
print(save(fig, "eda/04_roas_stored_vs_recomputed"))
# %% [markdown]
# ## 5. The two inventory files compared
# %%
iv, ivn = R["inventory"], R["inventoryNew"]
stats = pd.DataFrame({
    "damage rate": [iv.damaged_stock.sum() / iv.stock_received.sum(), ivn.damaged_stock.sum() / ivn.stock_received.sum()],
    "rows with damaged > received": [(iv.damaged_stock > iv.stock_received).mean(), (ivn.damaged_stock > ivn.stock_received).mean()],
}, index=["inventory (daily)", "inventoryNew (monthly)"])
display(stats)
rows_pm = ivn.groupby(["product_id", "date"]).size()
print("inventoryNew rows per product-month:", rows_pm.value_counts().sort_index().to_dict(), "| damage rate", round(stats.iloc[1, 0], 4))
assert round(stats.iloc[1, 0], 4) == 0.0385
fig, axs = new_fig(h=4.6, ncols=3)
for ax, col, ttl in zip(axs[:2], stats.columns, ["Damage rate (damaged / received)", "Rows where damaged exceeds received"]):
    vals = stats[col].values
    ax.bar([0, 1], vals, color=[GREY, GREEN], width=.55)
    for i, v in enumerate(vals):
        ax.text(i, v, f"{v:.1%}", ha="center", va="bottom", fontsize=11, fontweight="bold")
    ax.set_xticks([0, 1], ["daily\n(75,172 rows)", "monthly\n(18,105 rows)"]); ax.set_ylim(0, max(vals) * 1.2); ax.yaxis.set_visible(False)
    ax.spines[["left"]].set_visible(False); ax.set_title(ttl); ax.tick_params(length=0)
vc = rows_pm.value_counts().sort_index()
axs[2].bar(vc.index, vc.values, color=GREEN, width=.6)
for k, v in vc.items():
    axs[2].text(k, v, f"{v:,}", ha="center", va="bottom", fontsize=8.5)
axs[2].set_xlabel("Rows per product-month in inventoryNew"); axs[2].yaxis.set_visible(False); axs[2].spines[["left"]].set_visible(False)
axs[2].set_title("Monthly file repeats product x month"); axs[2].tick_params(length=0)
headline(fig, "The daily inventory file is not credible (54% damage); the monthly file (3.85%) is used, summed to product x month",
         "Damage rate and basic consistency of the two inventory files")
footnote(fig, "Source: data/raw inventory and inventoryNew. The clean layer sums inventoryNew to 5,571 product x month rows; 3.85% = damaged / received, as in docs/reconciliation.md.")
print(save(fig, "eda/05_inventory_files_compared"))
