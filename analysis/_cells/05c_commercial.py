# %% [markdown]
# ## D. Basket and price
# **Method.** Discount depth = 1 - price / MRP (mean 27.7%, range 15 to 40%) in quintiles; mean quantity, order value and stored margin % per quintile with bootstrap 95% CIs, Spearman correlations;
# category mix by stored segment as deviations from the overall mix, with a chi-square test on order counts.
# %%
o["disc_q"] = pd.qcut(o.discount, 5, labels=[f"Q{i}" for i in range(1, 6)])
qlab = o.groupby("disc_q", observed=True).discount.agg(["min", "max"]).map(lambda v: f"{v:.0%}")
qlab = [f"Q{i + 1}\n{a}-{b}" for i, (a, b) in enumerate(zip(qlab["min"], qlab["max"]))]
rho_q, p_q = stats.spearmanr(o.discount, o.quantity); rho_t, p_t = stats.spearmanr(o.discount, o.order_total); rho_m, _ = stats.spearmanr(o.discount, o.margin_percentage)
print(f"discount mean {o.discount.mean():.1%} | Spearman with quantity {rho_q:+.3f} (p = {p_q:.2f}), order total {rho_t:+.3f} (p = {p_t:.2f}), margin % {rho_m:+.2f}")
assert abs(rho_q - .006) < .002 and abs(p_q - .66) < .02
fig, axs = new_fig(h=4.5, ncols=3)
spec = [("quantity", "Units per order (mean, 95% CI)", "{:.2f}", rho_q, p_q), ("order_total", "Order value, ₹ (mean, 95% CI)", "{:,.0f}", rho_t, p_t), ("margin_percentage", "Stored margin % of the product (mean, 95% CI)", "{:.1f}", rho_m, 0)]
for ax, (col, ttl, fm, rho, p) in zip(axs, spec):
    g = o.groupby("disc_q", observed=True)[col]
    mu = g.mean(); ci_ = np.array([boot_ci(v.values, n=800) for _, v in g])
    ax.bar(range(5), mu, color=GREEN if col != "margin_percentage" else GREY, width=.62, yerr=[mu - ci_[:, 0], ci_[:, 1] - mu], error_kw=dict(ecolor=INK, capsize=3, elinewidth=1))
    for i, v in enumerate(mu): ax.text(i, ci_[i, 1] * 1.015, fm.format(v), ha="center", fontsize=8.5)
    ax.set_xticks(range(5), qlab, fontsize=8); ax.set_ylim(0, ci_[:, 1].max() * 1.15); ax.yaxis.set_visible(False); ax.spines[["left"]].set_visible(False); ax.tick_params(length=0)
    ax.set_title(ttl + (f"\nSpearman {rho:+.3f}, {pfmt(p)}" if col != "margin_percentage" else f"\nSpearman {rho:+.2f}: margin % is built from discount depth"), fontsize=9)
headline(fig, "Deeper discounts do not sell more or bigger baskets: quantity and order value are flat across discount-depth quintiles",
         "Discount depth quintiles (share off MRP, 15% to 40%). The stored margin % rises with depth only because it is derived from it")
footnote(fig, "Source: data/clean fact_orders, dim_product. Bars start at zero. Order value does not reconcile with item lines (audit), so basket analysis is limited to quantity (1 to 3, uniform) and the order header.")
print(save(fig, "ds/discount_depth"))
# %%
cs_ = pd.crosstab(o.category, o.segment); chi2, p_cs, dof, _ = stats.chi2_contingency(cs_); V = np.sqrt(chi2 / (cs_.values.sum() * (min(cs_.shape) - 1)))
lv = o.pivot_table(index="category", columns="segment", values="line_value", aggfunc="sum")
seg_share = lv / lv.sum(); overall_mix = o.groupby("category").line_value.sum() / o.line_value.sum()
dev = (seg_share.sub(overall_mix, axis=0) * 100)[["New", "Regular", "Premium", "Inactive"]].loc[overall_mix.sort_values(ascending=False).index]
print(f"category x segment chi-square p = {p_cs:.2f}, Cramer's V = {V:.3f} | largest deviation {dev.abs().max().max():.1f} points")
assert abs(p_cs - .16) < .02
fig, ax = new_fig(h=5.4, left=0.17)
sns.heatmap(dev, ax=ax, cmap=DIV, center=0, vmin=-6, vmax=6, annot=dev.map(lambda v: f"{v:+.1f}"), fmt="", annot_kws={"fontsize": 8.5}, linewidths=.7, linecolor="white", cbar_kws={"shrink": .75, "label": "points vs overall category share"})
ax.set_xlabel(""); ax.set_ylabel(""); ax.tick_params(length=0); plt.setp(ax.get_yticklabels(), rotation=0); ax.xaxis.tick_top()
ax.set_yticklabels([f"{c_} ({overall_mix[c_]:.1%})" for c_ in dev.index], rotation=0)
headline(fig, f"Every stored segment buys the same category mix: no cell is more than {dev.abs().max().max():.1f} points from the overall share (chi-square {pfmt(p_cs)})",
         "Share of line value by category within each stored segment minus the overall share, in percentage points; overall share in brackets")
footnote(fig, f"Source: data/clean fact_orders, dim_customer. Cramer's V = {V:.2f} (negligible). Segment groups hold 1,000 to 1,500 orders, so a gap of 2 to 3 points is within sampling noise. Line value basis (quantity x unit price).")
print(save(fig, "ds/category_by_segment"))
# %% [markdown]
# **So what.** Neither price depth nor segment shapes what customers buy here. A discount-depth test (cut the discount by 2 points in a few categories) is the way to learn the true response; this data cannot.
#
# ## E. Marketing funnel and efficiency
# **Method.** Impressions to clicks to conversions by channel; CTR and click-to-conversion rates with Wilson 95% CIs, cost per conversion with a bootstrap CI; Spearman correlations between funnel stages and revenue.
# %%
chn = mk.groupby("channel")[["impressions", "clicks", "conversions", "spend", "attributed_revenue"]].sum().loc[["App", "Email", "SMS", "Social Media"]]
tot = chn.sum()
chn["ctr"] = chn.clicks / chn.impressions; chn["cvr"] = chn.conversions / chn.clicks; chn["cpa"] = chn.spend / chn.conversions
ctr_ci = wilson(chn.clicks, chn.impressions); cvr_ci = wilson(chn.conversions, chn.clicks)
def cpa_ci(d, n=1000):
    sp, cv = d.spend.values, d.conversions.values; idx = rng.integers(0, len(d), (n, len(d)))
    return np.percentile(sp[idx].sum(1) / cv[idx].sum(1), [2.5, 97.5])
cpa_c = np.array([cpa_ci(d) for _, d in mk.groupby("channel")])[[0, 1, 2, 3]]
rho_cr, p_cr = stats.spearmanr(mk.conversions, mk.attributed_revenue)
ctr_all, cvr_all, cpa_all = tot.clicks / tot.impressions, tot.conversions / tot.clicks, tot.spend / tot.conversions
print(f"CTR {ctr_all:.1%}, click-to-conversion {cvr_all:.1%}, cost per conversion ₹{cpa_all:.1f}, revenue per conversion ₹{tot.attributed_revenue / tot.conversions:.0f} | conversions vs revenue Spearman {rho_cr:+.3f} (p = {p_cr:.2f}) | conversions per order {tot.conversions / N:.1f}")
assert round(ctr_all, 3) == .101 and round(cvr_all, 3) == .100 and round(cpa_all, 1) == 54.8
# %%
fig, axs = new_fig(h=4.6, ncols=4, gridspec_kw={"width_ratios": [1.5, 1, 1, 1]}, left=0.12)
a = axs[0]; vals = [tot.impressions, tot.clicks, tot.conversions]; labs = ["Impressions", "Clicks", "Conversions"]
a.barh(range(3), vals, color=[GREY, MIDGREEN, GREEN], height=.6)
for i, v in enumerate(vals):
    a.text(v + tot.impressions * .015, i, f"{v / 1e6:.2f} M" if v > 1e6 else f"{v / 1e3:,.0f} K", va="center", fontsize=9, fontweight="bold")
a.text(tot.impressions * .52, .5, f"{ctr_all:.1%} click", ha="center", fontsize=9, color=MUTED); a.text(tot.impressions * .52, 1.5, f"{cvr_all:.1%} convert", ha="center", fontsize=9, color=MUTED)
a.set_yticks(range(3), labs); a.invert_yaxis(); a.set_xlim(0, tot.impressions * 1.25); a.xaxis.set_visible(False); a.spines[["bottom", "left"]].set_visible(False); a.tick_params(length=0); a.set_title("All channels, true scale")
for ax, vals_, lo_, hi_, ttl, fm in [(axs[1], chn.ctr, ctr_ci[0], ctr_ci[1], "Click-through rate", "{:.1%}"), (axs[2], chn.cvr, cvr_ci[0], cvr_ci[1], "Click to conversion", "{:.1%}"), (axs[3], chn.cpa, cpa_c[:, 0], cpa_c[:, 1], "Cost per conversion, ₹", "{:.1f}")]:
    v = np.asarray(vals_); lo_, hi_ = np.asarray(lo_), np.asarray(hi_)
    ax.bar(range(4), v, color=GREEN, width=.62, yerr=[v - lo_, hi_ - v], error_kw=dict(ecolor=INK, capsize=3, elinewidth=1))
    for i in range(4): ax.text(i, hi_[i] * 1.02, fm.format(v[i]), ha="center", fontsize=8.5)
    ax.set_xticks(range(4), ["App", "Email", "SMS", "Social"], fontsize=8); ax.set_ylim(0, hi_.max() * 1.18); ax.yaxis.set_visible(False); ax.spines["left"].set_visible(False); ax.tick_params(length=0); ax.set_title(ttl, fontsize=9.5)
headline(fig, f"The funnel is identical in every channel ({ctr_all:.1%} click, {cvr_all:.1%} convert, ₹{cpa_all:.0f} per conversion) and conversions do not predict revenue (rho {rho_cr:+.2f})",
         f"Impressions to clicks to conversions, 5,400 campaign records. Bars with 95% CIs; zero baselines. Conversions vs attributed revenue per record: Spearman {rho_cr:+.3f}, {pfmt(p_cr)}")
footnote(fig, f"Source: data/clean fact_marketing. {tot.conversions / N:.0f} conversions per order in the order data and attributed revenue 2.9x order revenue mean the funnel is not linked to real orders. Report it, but do not optimise on it.")
print(save(fig, "ds/marketing_funnel"))
# %% [markdown]
# ## F. Inventory
# **Method.** Damage rate = damaged / received by category with Wilson 95% CIs and a chi-square test across categories; received stock compared with units sold in the order data.
# %%
iv = inv.merge(pr[["product_id", "category"]], on="product_id")
dm = iv.groupby("category")[["damaged_stock", "stock_received"]].sum(); dm["rate"] = dm.damaged_stock / dm.stock_received
dm["lo"], dm["hi"] = wilson(dm.damaged_stock, dm.stock_received); dm = dm.sort_values("rate", ascending=False)
p_dm = stats.chi2_contingency(np.c_[dm.damaged_stock, dm.stock_received - dm.damaged_stock])[1]
overall_d = iv.damaged_stock.sum() / iv.stock_received.sum()
sold = o.groupby("category").quantity.sum(); recv = iv.groupby("category").stock_received.sum()
sr = pd.DataFrame({"received": recv, "sold": sold}).sort_values("received", ascending=False); sr["ratio"] = sr.received / sr.sold
print(f"damage {overall_d:.2%} (categories {dm.rate.min():.2%} {dm.rate.idxmin()} to {dm.rate.max():.2%} {dm.rate.idxmax()}), chi-square {pfmt(p_dm)} | received {int(sr.received.sum()):,} vs sold {int(sr.sold.sum()):,} = {sr.received.sum() / sr.sold.sum():.1f}x")
assert round(overall_d, 4) == .0385 and abs(p_dm - .24) < .02 and int(sr.received.sum()) == 28779 and int(sr.sold.sum()) == 10034
fig, (a1, a2) = new_fig(h=4.9, ncols=2, gridspec_kw={"width_ratios": [1, 1.1]}, left=0.17)
y = np.arange(len(dm))
a1.errorbar(dm.rate * 100, y, xerr=[(dm.rate - dm.lo) * 100, (dm.hi - dm.rate) * 100], fmt="o", color=GREEN, capsize=2.5, ms=5)
a1.axvline(overall_d * 100, color=GREY, ls="--", lw=1); a1.text(overall_d * 100, -.9, f"overall {overall_d:.2%}", ha="center", fontsize=8.5, color=MUTED)
a1.set_yticks(y, dm.index); a1.set_ylim(len(dm) - .4, -1.3); a1.set_xlim(0, 7); a1.set_xlabel("Damage rate, % of units received (95% CI)"); clean_axes(a1, "x"); a1.set_title(f"Damage by category: {pfmt(p_dm)}", fontsize=9.5)
y2 = np.arange(len(sr)); hh = .38
a2.barh(y2 - hh / 2, sr.received, height=hh, color=GREEN, label="stock received"); a2.barh(y2 + hh / 2, sr.sold, height=hh, color=YELLOW, label="units sold (order data)")
for i, (_, r) in enumerate(sr.iterrows()): a2.text(r.received + 40, i - hh / 2, f"{r.ratio:.1f}x", va="center", fontsize=8.5, fontweight="bold")
a2.set_yticks(y2, sr.index); a2.invert_yaxis(); a2.set_xlim(0, sr.received.max() * 1.15); a2.xaxis.set_visible(False); a2.spines[["bottom", "left"]].set_visible(False); a2.tick_params(length=0); a2.legend(loc="lower right")
a2.set_title(f"Received vs sold units: {sr.received.sum() / sr.sold.sum():.1f}x overall", fontsize=9.5)
headline(fig, f"Damage is {overall_d:.2%} overall and 3.1% to 4.7% by category, all within noise; stock received is {sr.received.sum() / sr.sold.sum():.1f}x the units sold",
         "Left: damaged / received units by category with 95% Wilson intervals. Right: stock received (inventoryNew) vs units sold in the orders file")
footnote(fig, "Source: data/clean fact_inventory (inventoryNew summed to product x month) and fact_orders. Damaged stock is about ₹5.3 L at list price. The 2.9x gap probably reflects that the order file is a sample; no stock levels exist, so lost sales cannot be separated from waste.")
print(save(fig, "ds/inventory_damage_and_stock"))
# %% [markdown]
# **So what.** Damage differs by category no more than chance allows (binomial noise per product explains all product spread), so a category-level waste programme would target nothing real here.
# Reconciling inbound stock to sales needs real stock levels.
#
# ## G. Analyses considered and rejected
# | Analysis | Why not |
# |---|---|
# | Market-basket / affinity (association rules) | One item per order: there are no baskets. |
# | Store, rider or zone productivity | Store and rider ids are unique on every order (5,000 distinct), so there is nothing to compare. |
# | Geospatial / drive-time model of lateness | Only area names (316, about 16 orders each) and a distance column; no coordinates. Distance is unrelated to lateness (A1). |
# | Brand analysis | 267 brands for 268 products; every brand is a single product. |
# | Customer churn or lifetime-value prediction | No behavioural signal (flat retention, random orders): a model would learn noise. The cross-validated AUCs in A1 (about 0.5 for late and for poor experience) are the same warning. |
# | Sentiment or topic mining of feedback text | 25 template sentences, and sentiment is a deterministic function of rating. |
# | Price elasticity / promotion lift | Price varies by product, not over time, and discount depth does not move quantity (D); no promotion calendar exists. |
# | Anomaly detection on daily revenue | Monthly CV is 5.5% and the series is stationary white noise (ADF p = 0.001, Ljung-Box p = 0.85): there is nothing to flag. |
# | Seasonality decomposition (STL) | 19 full months cover under two cycles; seasonal naive is the worst backtest model (7.1% MAPE). |
# | Attribution of orders to campaigns | No key between marketing and orders, and attributed revenue is 2.9x order revenue. |
# %%
SUMMARY = {
    "late rate": f"{late_rate:.1%} (no driver: smallest factor p = {min(v[0] for v in tests.values()):.2f}, CV AUC {auc_late:.2f})",
    "poor experience": f"{share['Late only']:.1%} late only, {share['Low rating only']:.1%} low rating only, {share['Both']:.1%} both (independence p = {p_ind:.2f})",
    "revenue YoY (Apr-Oct)": f"{yoy:+.1%}: volume {e_y[0] / 1e5:+.2f} L, mix {e_y[1] / 1e5:+.2f} L, AOV {e_y[2] / 1e5:+.2f} L",
    "retention M+1..M+6": f"{np.mean(list(mean_k.values())):.1%} flat",
    "RFM champions": f"{SEGS.loc['Champions', 'cust_share']:.1%} of customers, {champ_obs:.1%} of revenue (random: {champ_sim.mean():.1%})",
    "Gini / top 20%": f"{g_obs:.3f} / {top20:.1%}",
    "discount vs quantity": f"Spearman {rho_q:+.3f} (p = {p_q:.2f})",
    "funnel": f"CTR {ctr_all:.1%}, CVR {cvr_all:.1%}, cost per conversion ₹{cpa_all:.1f}",
    "damage": f"{overall_d:.2%}, category chi-square {pfmt(p_dm)}",
}
display(pd.Series(SUMMARY, name="key result").to_frame())
