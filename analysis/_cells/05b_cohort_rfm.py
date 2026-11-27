# %% [markdown]
# ## B. Cohort analysis
# **Method.** Customers are grouped by the month of their first order (the registration date is unusable: 51% of orders precede it). Retention = share of a cohort with an order
# in month k after its first order; cohorts are masked where month k lies beyond the data (Nov 2024 is a partial month, as in the data science review). Revenue per acquired customer is cumulated by k.
# Time to second order uses Kaplan-Meier because customers without a second order are censored at the data end, not "never".
# %%
fo_ = o.groupby("customer_id").order_date.min().rename("first")
c = o.merge(fo_, on="customer_id")
c["cohort"] = c["first"].dt.to_period("M"); c["cm"] = c.order_date.dt.to_period("M")
c["k"] = (c.cm.dt.year - c.cohort.dt.year) * 12 + (c.cm.dt.month - c.cohort.dt.month)
coh = c.groupby(["cohort", "k"]).customer_id.nunique().unstack(fill_value=0)
size = coh[0]
ret = coh.div(size, axis=0).astype(float)
last_m = c.cm.max()
for ch_ in ret.index:
    for k in ret.columns:
        if (ch_ + int(k)) > last_m:
            ret.loc[ch_, k] = np.nan
mean_k = {k: float(ret[k].mean()) for k in range(1, 7)}
print("mean retention M+1..M+6:", {k: round(v, 3) for k, v in mean_k.items()}, "| cohorts", len(ret), "| sizes", int(size.min()), "to", int(size.max()))
for k, ref in zip(range(1, 7), [.085, .094, .082, .098, .09, .083]):
    assert abs(mean_k[k] - ref) < .0015, (k, mean_k[k], ref)
pooled = {k: coh[k][[ch_ for ch_ in coh.index if (ch_ + k) <= last_m]].sum() / size[[ch_ for ch_ in coh.index if (ch_ + k) <= last_m]].sum() for k in range(1, 7)}
print("customer-weighted retention M+1..M+6:", {k: round(float(v), 3) for k, v in pooled.items()})
# %%
KMAX = 12
rp = ret.loc[:, 1:KMAX].copy()
rp.index = [f"{p.strftime('%b-%y')}  (n = {int(size[p])})" for p in rp.index]
allrow = ret.loc[:, 1:KMAX].mean().to_frame().T; allrow.index = ["All cohorts, mean"]
M = pd.concat([rp, allrow]) * 100
fig, ax = new_fig(h=6.6, left=0.14)
ann = M.map(lambda v: "" if pd.isna(v) else f"{v:.0f}")
sns.heatmap(M, ax=ax, cmap=SEQ_LIGHT, vmin=0, vmax=30, annot=ann, fmt="", annot_kws={"fontsize": 7.5}, linewidths=.5, linecolor="white", cbar_kws={"shrink": .7, "label": "% of cohort ordering in month k"})
ax.axhline(len(rp), color=INK, lw=1.2); ax.set_xlabel("Months since first order"); ax.set_ylabel(""); ax.tick_params(length=0); plt.setp(ax.get_yticklabels(), rotation=0, fontsize=8)
ax.set_xticklabels([f"M+{k}" for k in range(1, KMAX + 1)], rotation=0)
headline(fig, f"Retention is flat at about {np.mean(list(mean_k.values())):.0%} in every month after the first order: no decay, no maturing cohort",
         "Share of each first-order-month cohort that orders again k months later (blank = month not yet observed). Cohort size in brackets; scale starts at 0")
footnote(fig, "Source: data/clean fact_orders; cohort = month of first order in the data (Mar 2023 holds customers who may have ordered earlier). Cohorts of 5 to 233 customers: single cells are noisy. Real retention decays; this flat line fits random order assignment.")
print(save(fig, "ds/cohort_retention"))
# %%
rev_ck = c.groupby(["cohort", "k"]).order_total.sum().unstack(fill_value=0)
rpc = rev_ck.div(size, axis=0)
for ch_ in rpc.index:
    for k in rpc.columns:
        if (ch_ + int(k)) > last_m:
            rpc.loc[ch_, k] = np.nan
cum = rpc.fillna(0).cumsum(axis=1).where(rpc.notna())
inc = {k: rev_ck[k][[x for x in rev_ck.index if (x + k) <= last_m]].sum() / size[[x for x in rev_ck.index if (x + k) <= last_m]].sum() for k in range(0, 13)}
cum_pool = np.cumsum(list(inc.values()))
print("first order per customer", round(inc[0]), "| later months, mean per customer per month", round(np.mean([inc[k] for k in range(1, 13)])), "| cumulative at M+12", round(cum_pool[12]))
# %% [markdown]
# ### Time to second order
# %%
from statsmodels.duration.survfunc import SurvfuncRight
s2 = o.sort_values(["customer_id", "order_date", "order_id"])
g1 = s2.groupby("customer_id").order_date.agg(["min", lambda x: x.iloc[1] if len(x) > 1 else pd.NaT]); g1.columns = ["first", "second"]
g1["event"] = g1.second.notna().astype(int)
g1["days"] = np.where(g1.event == 1, (g1.second - g1["first"]).dt.days, (END - g1["first"]).dt.days)
obs = g1[g1.event == 1].days
sf = SurvfuncRight(g1.days.values.astype(float), g1.event.values)
t_ = sf.surv_times; cdf = 1 - sf.surv_prob; se = sf.surv_prob_se
med_obs, p90 = obs.median(), obs.quantile(.9)
t_med = float(t_[np.argmax(cdf >= .5)]) if (cdf >= .5).any() else np.nan
print(f"observed second orders n = {len(obs):,}, median {med_obs:.0f} days, P90 {p90:.0f} | KM share reordered by 365 days: {float(np.interp(365, t_, cdf)):.1%} | KM median {t_med}")
assert len(obs) == 1492 and med_obs == 134
# %%
fig, (a1, a2) = new_fig(h=4.8, ncols=2)
curves = [x for x in cum.index if size[x] >= 40]
for x in curves:
    a1.plot(range(0, 13), cum.loc[x, 0:12].values, color=LTGREY, lw=1)
a1.plot(range(0, 13), cum_pool, color=GREEN, lw=3, label="all cohorts, weighted")
a1.set_xlabel("Months since first order"); a1.set_ylabel("Cumulative revenue per acquired customer, ₹"); a1.set_ylim(0, 5800); clean_axes(a1)
a1.text(12, cum_pool[12], f"  ₹{cum_pool[12]:,.0f}", va="center", fontsize=9, color=GREEN, fontweight="bold")
a1.text(12, 900, "first order ₹%s" % format(inc[0], ",.0f") + chr(10) + "then about ₹%s a month" % format(np.mean([inc[k] for k in range(1, 13)]), ",.0f"), fontsize=9.5, va="bottom", ha="right")
a1.set_title(f"Revenue per customer: {len(curves)} cohorts (grey) and the average")
a2.hist(obs, bins=np.arange(0, 600, 30), color=GREEN, alpha=.85)
a2.axvline(med_obs, color=INK, ls="--", lw=1); a2.text(med_obs + 6, a2.get_ylim()[1] * .95, "median %d days, P90 %d" % (med_obs, p90) + chr(10) + "(customers who reordered)" + chr(10) + "Kaplan-Meier median %d days;" % t_med + chr(10) + "%.0f%% reorder within a year" % (100 * float(np.interp(365, t_, cdf))) + chr(10) + "(counts customers still waiting)", va="top", fontsize=9)
a2.set_xlabel("Days from first to second order (customers who reordered, n = 1,492)"); a2.set_ylabel("Customers"); clean_axes(a2)
a2.set_title(f"Time to second order; {1 - g1.event.mean():.0%} of customers have not reordered yet")
headline(fig, f"A customer's value grows by a steady ₹{np.mean([inc[k] for k in range(1, 13)]):,.0f} a month after the first order, and half of new customers have reordered after about {t_med / 30.4:.0f} months (Kaplan-Meier median {t_med:.0f} days)",
         "Left: cumulative revenue per acquired customer by cohort. Right: distribution of days to the second order (observed reorders only)")
footnote(fig, "Source: data/clean fact_orders. Cohort curves end where the data end, so later months rest on fewer cohorts. The histogram covers observed reorders only (it understates the wait); the Kaplan-Meier median counts customers still waiting.")
print(save(fig, "ds/cohort_revenue_and_second_order"))
# %% [markdown]
# **So what.** There is no cohort effect to manage: every cohort adds about the same revenue per month, and retention does not decay. A reorder cycle of about 4 to 5 months makes a
# "60-day reorder" a harsh KPI for groceries; in real data a day-90 win-back nudge is the natural test (see the review).
#
# ## C. RFM segmentation and the Pareto curve
# **Method.** Recency (days since last order), frequency (orders) and monetary value (revenue) scored in quintiles (5 = best; frequency ties broken by revenue, recency by rank) for the
# 2,172 ordering customers, then grouped into six actionable segments. To judge whether the segments are real, the same procedure is run 100 times after shuffling which customer each order belongs to.
# %%
def rfm(df, end=END):
    r = df.groupby("customer_id").agg(last=("order_date", "max"), f=("order_id", "size"), m=("order_total", "sum"))
    r["r_days"] = (end - r["last"]).dt.days
    r["R"] = pd.qcut(r.r_days.rank(method="first"), 5, labels=[5, 4, 3, 2, 1]).astype(int)
    r["F"] = pd.qcut((r.f * 1e7 + r.m).rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    r["M"] = pd.qcut(r.m.rank(method="first"), 5, labels=[1, 2, 3, 4, 5]).astype(int)
    R_, F_ = r.R, r.F
    r["segment"] = np.select([(R_ >= 4) & (F_ >= 4), (R_ >= 3) & (F_ >= 3), (R_ <= 2) & (F_ >= 3), (R_ >= 4) & (F_ <= 2), (R_ == 3) & (F_ <= 2)],
                             ["Champions", "Loyal", "At risk", "New / recent", "Needs attention"], "Hibernating")
    return r
rf = rfm(o)
SEGS = rf.groupby("segment").agg(customers=("m", "size"), revenue=("m", "sum"), orders=("f", "mean"), recency=("r_days", "mean"))
SEGS["cust_share"] = SEGS.customers / SEGS.customers.sum(); SEGS["rev_share"] = SEGS.revenue / SEGS.revenue.sum()
SEGS = SEGS.sort_values("rev_share", ascending=False)
display(SEGS.round(3))
assert SEGS.customers.sum() == 2172 and round(SEGS.revenue.sum(), 2) == 11009308.50
sim = []
for _ in range(100):
    sh = o.assign(customer_id=rng.permutation(o.customer_id.values))
    sg = rfm(sh).groupby("segment").agg(n=("m", "size"), rev=("m", "sum"))
    sim.append((sg.rev / sg.rev.sum()).reindex(SEGS.index).fillna(0).values)
sim = np.array(sim)
champ_obs = SEGS.loc["Champions", "rev_share"]; champ_sim = sim[:, list(SEGS.index).index("Champions")]
print(f"Champions revenue share observed {champ_obs:.1%} | random assignment mean {champ_sim.mean():.1%} (95% range {np.percentile(champ_sim, 2.5):.1%} to {np.percentile(champ_sim, 97.5):.1%})")
# %%
fig, (a1, a2) = new_fig(h=4.9, ncols=2, gridspec_kw={"width_ratios": [1.15, 1]}, left=0.13)
y = np.arange(len(SEGS)); h_ = .36
a1.barh(y - h_ / 2, SEGS.cust_share, height=h_, color=GREY, label="share of customers")
a1.barh(y + h_ / 2, SEGS.rev_share, height=h_, color=GREEN, label="share of revenue")
for i, (n, r) in enumerate(SEGS.iterrows()):
    a1.text(r.rev_share + .006, i + h_ / 2, f"{r.rev_share:.1%}", va="center", fontsize=8.5, fontweight="bold")
    a1.text(r.cust_share + .006, i - h_ / 2, f"{r.cust_share:.1%}  ({int(r.customers)})", va="center", fontsize=8, color=MUTED)
    lo, hi = np.percentile(sim[:, list(SEGS.index).index(n)], [2.5, 97.5])
    a1.plot([lo, hi], [i + h_ / 2 + .27] * 2, color=INK, lw=1.2); a1.plot([lo, lo], [i + h_ / 2 + .22, i + h_ / 2 + .32], color=INK, lw=1); a1.plot([hi, hi], [i + h_ / 2 + .22, i + h_ / 2 + .32], color=INK, lw=1)
a1.set_yticks(y, SEGS.index); a1.invert_yaxis(); a1.set_xlim(0, .5); a1.xaxis.set_visible(False); a1.spines[["bottom", "left"]].set_visible(False); a1.tick_params(length=0)
a1.legend(loc="lower right"); a1.set_title("Segment size vs revenue (black line = range under random assignment)", fontsize=9.5)
hm = rf.pivot_table(index="R", columns="F", values="m", aggfunc="mean").sort_index(ascending=False)
cn = rf.pivot_table(index="R", columns="F", values="m", aggfunc="size").sort_index(ascending=False)
sns.heatmap(hm / 1e3, ax=a2, cmap=SEQ_LIGHT, vmin=0, annot=(hm / 1e3).map(lambda v: f"{v:.1f}K") + "\nn=" + cn.astype(str), fmt="", annot_kws={"fontsize": 7.5}, linewidths=.6, linecolor="white", cbar_kws={"shrink": .7, "label": "mean revenue per customer, ₹ thousand"})
a2.set_xlabel("Frequency score (5 = most orders)"); a2.set_ylabel("Recency score (5 = most recent)"); a2.tick_params(length=0); a2.set_title("Revenue per customer by R and F score", fontsize=9.5)
headline(fig, f"Champions are {SEGS.loc['Champions', 'cust_share']:.0%} of customers and {champ_obs:.0%} of revenue; random assignment gives {champ_sim.mean():.0%}, so the segments are partly mechanical",
         "RFM quintile scores for 2,172 ordering customers, grouped into six segments; the black line is the 95% range when orders are randomly reassigned to customers")
footnote(fig, "Source: data/clean fact_orders (revenue = order_total). Recency measured to 4 Nov 2024. Frequency drives the segments; with orders assigned at random a similar split appears, so test RFM targeting on real data before acting.")
print(save(fig, "ds/rfm_segments"))
# %%
cr = rf.m.sort_values(ascending=False).values
cumshare = np.cumsum(cr) / cr.sum(); nc = len(cr); xx = np.arange(1, nc + 1) / nc
def gini(v):
    v = np.sort(np.asarray(v, float)); n = len(v)
    return float((2 * np.arange(1, n + 1) - n - 1) @ v / (n * v.sum()))
g_obs = gini(cr); g_ci = boot_ci(cr, gini, n=400)
top10, top20 = cumshare[int(nc * .1) - 1], cumshare[int(nc * .2) - 1]
sims, simg, simo = [], [], []
for _ in range(200):
    # every customer keeps at least one order (as in the data), the rest are assigned at random
    perm = rng.permutation(N); cid = np.empty(N, dtype=int); cid[perm[:nc]] = np.arange(nc); cid[perm[nc:]] = rng.integers(0, nc, N - nc)
    rv = np.bincount(cid, weights=o.order_total.values, minlength=nc)
    simg.append(gini(rv)); sims.append(np.cumsum(np.sort(rv)[::-1]) / rv.sum()); simo.append(np.bincount(np.bincount(cid, minlength=nc), minlength=14)[:14] / nc)
sims = np.array(sims); simo = np.array(simo)
opc = rf.f.value_counts().sort_index(); opc = opc.reindex(range(1, 14), fill_value=0) / nc
print(f"top 10% {top10:.1%}, top 20% {top20:.1%}, Gini {g_obs:.3f} (95% CI {g_ci[0]:.3f} to {g_ci[1]:.3f}) | random assignment Gini {np.mean(simg):.3f} | var/mean of orders per customer {rf.f.var():.2f}/{rf.f.mean():.2f}")
assert round(top20, 3) == .409 and round(top10, 3) == .240 and round(g_obs, 3) == .366
fig, (a1, a2) = new_fig(h=4.8, ncols=2)
a1.fill_between(xx, np.percentile(sims, 2.5, axis=0), np.percentile(sims, 97.5, axis=0), color=LTGREY, alpha=.9, label="random assignment (95% range)", lw=0)
a1.plot(xx, cumshare, color=GREEN, lw=2.5, label="observed"); a1.plot([0, 1], [0, 1], color=GREY, ls=":", lw=1)
a1.scatter([.2], [top20], color=GREEN, zorder=5); a1.annotate(f"top 20% of customers = {top20:.1%} of revenue\n(top 10% = {top10:.1%}; real retail is 60 to 80%)", (.2, top20), xytext=(.33, .30), fontsize=9, arrowprops=dict(arrowstyle="-", color=MUTED))
a1.set_xlabel("Share of customers, biggest first"); a1.set_ylabel("Cumulative share of revenue"); a1.set_xlim(0, 1); a1.set_ylim(0, 1.02); clean_axes(a1, "both"); a1.legend(loc="lower right")
a1.set_title(f"Pareto curve: Gini {g_obs:.3f} (95% CI {g_ci[0]:.2f} to {g_ci[1]:.2f}); random {np.mean(simg):.3f}")
xs = np.arange(1, 10)
a2.bar(xs - .2, opc.loc[1:9].values * 100, width=.4, color=GREEN, label="observed")
a2.bar(xs + .2, simo[:, 1:10].mean(0) * 100, width=.4, color=LTGREY, label="random assignment")
a2.set_xticks(xs); a2.set_xlabel("Orders per customer"); a2.set_ylabel("% of ordering customers"); clean_axes(a2); a2.legend()
a2.set_title(f"Fewer heavy buyers than chance: variance {rf.f.var():.2f} vs mean {rf.f.mean():.2f}")
headline(fig, f"Revenue concentration is close to random: the top 20% of customers hold {top20:.0%} of revenue (Gini {g_obs:.2f} vs {np.mean(simg):.2f} random), far below the 60 to 80% of real retail",
         "Customer revenue concentration (left) and the distribution of orders per customer (right) against 200 random reassignments of the same 5,000 orders")
footnote(fig, "Source: data/clean fact_orders, 2,172 ordering customers. Random band: 200 reassignments in which every customer keeps at least one order. The observed curve sits on or just above that band: there are no 'whales'. Orders per customer is under-dispersed (variance below mean), unlike real customer bases.")
print(save(fig, "ds/pareto_customers"))
# %% [markdown]
# **So what.** Behavioural RFM gives groups that are usable on paper (a third of customers carry about half of revenue), but they are about what a random assignment of the same orders would produce.
# Use RFM in CRM (replacing the stored segment, which is null) but treat the segment gaps as hypotheses until real data confirm them.
