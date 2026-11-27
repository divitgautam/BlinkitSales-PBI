# %% [markdown]
# # 02 · Exploratory data analysis
# What the cleaned data look like before any modelling: distributions, the hour x weekday pattern, mix, correlations and the monthly trend.
# Honest reading throughout: the distributions are close to uniform and the correlations are near zero, which is a property of the (synthetic-looking) source.
# %%
import sys
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
from scipy import stats
from IPython.display import display
from viz_style import *
from data_io import *
o = orders_enriched()
mk, inv = clean("fact_marketing"), clean("fact_inventory")
H = headline_numbers(o, mk, inv)
print(len(o), "orders |", f"revenue {H['revenue']:,.2f}", "| on-time", f"{H['on_time']:.1%}", "| rating", round(H["avg_rating"], 2))
# %% [markdown]
# ## 1. Distributions of order value, minutes late, distance and rating
# %%
fig, axs = new_fig(h=6.2, nrows=2, ncols=2)
a = axs[0, 0]
a.hist(o.order_total, bins=40, color=GREEN, alpha=.9)
med = o.order_total.median(); a.axvline(med, color=INK, lw=1, ls="--")
a.text(med, a.get_ylim()[1] * .95, f"  median ₹{med:,.0f}", fontsize=8.5, va="top")
a.set_title(f"Order value (n = {len(o):,}): broad and right-skewed"); a.set_xlabel("₹ per order"); a.set_ylabel("Orders"); clean_axes(a)
a = axs[0, 1]
vals = np.arange(-5, 31)
cnt = o.minutes_late.value_counts().reindex(vals, fill_value=0)
a.bar(vals, cnt.values, color=[GREEN if v <= 5 else YELLOW for v in vals], width=.9)
a.set_title("Minutes late vs promise: three flat plateaus"); a.set_xlabel("Minutes late (negative = early)"); a.set_ylabel("Orders"); clean_axes(a)
a.text(-5, cnt.max() * 1.02, "on time (up to 5 min late)", color=GREEN, fontsize=8.5, fontweight="bold")
a.text(17, cnt.max() * 1.02, f"late ({H['late']:.1%})", color="#B98300", fontsize=8.5, fontweight="bold")
a.set_ylim(0, cnt.max() * 1.12)
a = axs[1, 0]
a.hist(o.distance_km, bins=36, color=GREEN, alpha=.9)
a.set_title("Delivery distance: uniform 0.5 to 5 km"); a.set_xlabel("km"); a.set_ylabel("Orders"); clean_axes(a)
a = axs[1, 1]
rc = o.rating.value_counts().sort_index()
a.bar(rc.index, rc.values, color=[YELLOW if r <= 2 else GREEN for r in rc.index], width=.65)
for r, v in rc.items():
    a.text(r, v, f"{v / len(o):.0%}", ha="center", va="bottom", fontsize=9)
a.set_title(f"Rating: mean {H['avg_rating']:.2f}, {(o.rating <= 2).mean():.0%} rate 1-2 stars"); a.set_xlabel("Stars"); a.set_ylabel("Orders"); clean_axes(a)
a.set_ylim(0, rc.max() * 1.12)
h_ = np.histogram(o.minutes_late, bins=10)[0]
print("minutes_late max/min bin ratio", round(h_.max() / h_.min(), 1), "| order_total CV", round(o.order_total.std() / o.order_total.mean(), 2))
headline(fig, "Distance is uniform, order value is broad and delay falls in three flat plateaus; nothing clusters or peaks",
         "Distribution of the four order-level measures, full period (Mar 2023 to 4 Nov 2024)")
footnote(fig, "Source: data/clean fact_orders. Yellow marks late deliveries (status not On Time) and 1-2 star ratings, the two parts of the poor-experience definition.")
print(save(fig, "eda/06_distributions"))
# %% [markdown]
# ## 2. Hour x weekday
# %%
hw = o.pivot_table(index="dow_name", columns="order_hour", values="order_id", aggfunc="count", fill_value=0).reindex(["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"])
p_hour = stats.chisquare(o.order_hour.value_counts().reindex(range(24), fill_value=0)).pvalue
p_dow = stats.chisquare(o.dow.value_counts().sort_index()).pvalue
chi_all = stats.chi2_contingency(hw.values)
print("hour p", round(p_hour, 3), "| weekday p", round(p_dow, 3), "| hour x weekday independence p", round(chi_all[1], 3), "| min/max cell", hw.values.min(), hw.values.max())
fig, ax = new_fig(h=4.2, left=0.06)
sns.heatmap(hw, ax=ax, cmap=SEQ_LIGHT, vmin=0, annot=True, fmt="d", annot_kws={"fontsize": 7.5}, linewidths=.5, linecolor="white",
            cbar_kws={"shrink": .8, "label": "Orders in the cell"})
ax.set_xlabel("Hour of day"); ax.set_ylabel(""); ax.tick_params(length=0)
headline(fig, "There is no rush hour and no weekend lift: order counts per hour and weekday differ only by sampling noise",
         f"Orders by weekday and hour. Hour uniform: {pfmt(p_hour)}; weekday uniform: {pfmt(p_dow)}; independence of the two: {pfmt(chi_all[1])}")
footnote(fig, "Source: data/clean fact_orders. Colour scale starts at zero, so a flat picture means flat demand. Cells hold 5 to 40 orders, so single cells are noisy.")
print(save(fig, "eda/07_hour_weekday_heatmap"))
# %% [markdown]
# ## 3. Category and payment mix
# %%
cat = o.groupby("category").line_value.sum().sort_values(ascending=False)
pay = o.payment_method.value_counts()
lo, hi = wilson(pay.values, len(o))
chi_pay = stats.chisquare(pay.values).pvalue
fig, (a1, a2) = new_fig(h=4.8, ncols=2, gridspec_kw={"width_ratios": [1.5, 1]}, left=0.17)
bar_h(a1, list(cat.index), (cat / cat.sum()).values, fmt=lambda v: f"{v:.1%}", highlight=[0])
a1.set_title("Share of line value by category (not order revenue)")
x = np.arange(len(pay))
a2.bar(x, pay.values / len(o), color=GREEN, width=.55, yerr=[pay.values / len(o) - lo, hi - pay.values / len(o)], error_kw=dict(ecolor=INK, capsize=3, elinewidth=1))
for i, v in enumerate(pay.values):
    a2.text(i, hi[i] + .004, f"{v / len(o):.1%}", ha="center", va="bottom", fontsize=9)
a2.set_xticks(x, pay.index); a2.set_ylim(0, .34); a2.yaxis.set_visible(False); a2.spines[["left"]].set_visible(False); a2.tick_params(length=0)
a2.set_title(f"Payment method, share of orders (95% CI), {pfmt(chi_pay)} vs equal")
print((cat / cat.sum()).round(3).head(3).to_dict())
assert round(cat.iloc[0] / cat.sum(), 3) == 0.129 and cat.index[0] == "Dairy & Breakfast" and round(cat.sum() / 1e5, 2) == 49.72
headline(fig, "Dairy & Breakfast leads at 12.9% of line value, but categories are spread evenly and payment methods split four ways",
         "Left: category share of quantity x unit price (₹49.72 L in total). Right: orders by payment method")
footnote(fig, "Source: data/clean fact_orders. Category mix uses line value because order_total does not reconcile with item lines (see audit); bars start at zero. Yellow = top category.")
print(save(fig, "eda/08_category_payment_mix"))
# %% [markdown]
# ## 4. Correlation heatmap (Spearman)
# %%
cols = {"order_total": "Order total", "line_value": "Line value", "quantity": "Quantity", "unit_price": "Unit price", "discount": "Discount depth",
        "margin_percentage": "Margin %", "distance_km": "Distance", "minutes_late": "Minutes late", "rating": "Rating", "order_hour": "Hour"}
C = o[list(cols)].corr(method="spearman").rename(index=cols, columns=cols)
mech = {frozenset(p) for p in [("Line value", "Quantity"), ("Line value", "Unit price"), ("Margin %", "Discount depth")]}
pairs = [(a, b, C.loc[a, b]) for i, a in enumerate(C.index) for b in C.columns[:i]]
non_mech = [abs(v) for a, b, v in pairs if frozenset((a, b)) not in mech]
print("max |rho| outside the mechanical pairs:", round(max(non_mech), 3), "| mechanical:", {tuple(k): round(C.loc[tuple(k)[0], tuple(k)[1]], 2) for k in mech})
Cp = C.iloc[1:, :-1]
mask = np.triu(np.ones_like(Cp, dtype=bool), k=1)
fig, ax = new_fig(h=5.4, left=0.12, pad=0.7)
sns.heatmap(Cp, mask=mask, ax=ax, cmap=DIV, center=0, vmin=-1, vmax=1, annot=True, fmt=".2f", annot_kws={"fontsize": 8},
            linewidths=.6, linecolor="white", cbar_kws={"shrink": .7, "label": "Spearman correlation"})
ax.tick_params(length=0); plt.setp(ax.get_xticklabels(), rotation=35, ha="right")
headline(fig, f"Beyond two built-in links (price x quantity = line value; margin % = discount depth), correlations stay within {max(non_mech):.2f} of zero",
         "Spearman correlation between order-level numeric measures, lower triangle")
footnote(fig, "Source: data/clean fact_orders, dim_product. With no relationship, about +/-0.03 is noise at n = 5,000; the -0.07 to -0.08 on discount and price follow from discount = 1 - price / MRP. Delay, distance and rating are unrelated (0.00 to -0.01).")
print(save(fig, "eda/09_correlation_heatmap"))
# %% [markdown]
# ## 5. Monthly trend with the partial months marked
# %%
m = o.groupby("month_start").agg(revenue=("order_total", "sum"), orders=("order_id", "size"))
m["full"] = ~m.index.isin(PARTIAL)
full = m[m.full]
mean_full = full.revenue.mean()
print(m.round(0).tail(4).to_dict("index"))
print("19 full months, mean revenue", round(mean_full), "| CV", round(full.revenue.std() / mean_full, 3), "| max/min", round(full.revenue.max() / full.revenue.min(), 2))
assert len(full) == 19 and round(full.loc["2024-10-01", "revenue"]) == 537703
fig, (a1, a2) = new_fig(h=5.4, nrows=2, sharex=True, gridspec_kw={"height_ratios": [2.2, 1]})
a1.plot(full.index, full.revenue / 1e5, color=GREEN, marker="o", ms=4, lw=2, solid_joinstyle="miter")
for i, (d, r) in enumerate(m[~m.full].revenue.items()):
    a1.plot(d, r / 1e5, marker="o", mfc="white", mec=GREY, color=GREY, ms=6, ls="none")
    a1.annotate("partial month\n(not comparable)", (d, r / 1e5), xytext=(0, 14 if i == 0 else 16), textcoords="offset points", ha="center", fontsize=8, color=MUTED)
a1.axhline(mean_full / 1e5, color=GREY, ls="--", lw=1)
a1.text(m.index[2], mean_full / 1e5 - .12, f"mean of 19 full months ₹{mean_full / 1e5:.2f} L", ha="left", va="top", fontsize=8.5, color=MUTED)
a1.set_ylim(0, 8); a1.set_ylabel("Revenue, ₹ lakh"); clean_axes(a1)
a1.set_title("Revenue (order_total), zero baseline")
a2.bar(m.index, m.orders, width=20, color=[GREEN if f else LTGREY for f in m.full])
a2.set_ylabel("Orders"); clean_axes(a2); a2.set_title("Orders per month (grey = partial)")
headline(fig, f"Revenue holds at about ₹{mean_full / 1e5:.1f} L a month (±{full.revenue.std() / mean_full:.0%}); Mar 2023 and Nov 2024 are partial months",
         "Monthly revenue and order count, Mar 2023 to Nov 2024")
footnote(fig, "Source: data/clean fact_orders. Mar 2023 starts on the 16th (120 orders) and Nov 2024 ends on the 4th (30 orders); both are excluded from trends, YoY and the forecast.")
print(save(fig, "eda/10_monthly_trend"))
