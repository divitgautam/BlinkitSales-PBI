# %% [markdown]
# # 05 · Deep dives
# Root-cause analysis, cohorts, RFM, basket and price, marketing funnel and inventory. Each section states the method, shows the result with its
# uncertainty and ends with a so-what. Numbers that overlap `docs/reconciliation.md` are asserted against it.
#
# **Contents:** A. Root cause: lateness, poor experience, revenue variance - B. Cohorts - C. RFM and Pareto - D. Basket and price - E. Marketing funnel - F. Inventory - G. Analyses considered and rejected.
# %%
import sys, warnings
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
warnings.filterwarnings("ignore")
from scipy import stats
import statsmodels.api as sm, statsmodels.formula.api as smf
from sklearn.linear_model import LogisticRegression
from sklearn.model_selection import StratifiedKFold, cross_val_predict
from sklearn.metrics import roc_auc_score
from IPython.display import display
from viz_style import *
from data_io import *
o = orders_enriched(); mk = clean("fact_marketing"); inv = clean("fact_inventory"); pr = clean("dim_product")
H = headline_numbers(o, mk, inv)
END = o.order_date.max()
rng = np.random.default_rng(2026)
N = len(o); late_rate = o.is_late.mean()
assert N == 5000 and round(late_rate, 3) == .306 and round(o.poor_experience.mean(), 3) == .458
# %% [markdown]
# ## A1. Root cause of lateness: what separates late orders from on-time ones?
# **Method.** Late rate (status not On Time, 30.6%) by distance band, time of day, weekday, category and payment with Wilson 95% CIs; chi-square test per factor
# (area has 316 levels, so it is shown as a funnel plot against binomial limits); a logistic model on all drivers with a likelihood-ratio test, and a cross-validated AUC
# as a predictability ceiling (0.5 = no better than a coin).
# %%
FACT = {"Distance band": "dist_band", "Time of day": "day_part", "Weekday": "dow_name", "Category": "category", "Payment": "payment_method"}
ORDER = {"dow_name": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]}
tests, tabs = {}, {}
for name, col in FACT.items():
    t = pd.crosstab(o[col], o.is_late)
    if col in ORDER:
        t = t.reindex(ORDER[col])
    chi2, p, dof, _ = stats.chi2_contingency(t)
    tests[name] = (p, chi2, dof, np.sqrt(chi2 / (t.values.sum() * (min(t.shape) - 1))))
    k, n = t[True].values, t.sum(1).values
    lo, hi = wilson(k, n)
    tabs[name] = pd.DataFrame({"late": k, "n": n, "rate": k / n, "lo": lo, "hi": hi}, index=t.index.astype(str))
area = o.groupby("area").is_late.agg(["sum", "size"])
p_area = stats.chi2_contingency(pd.crosstab(o.area, o.is_late))[1]
d = o.assign(late=o.is_late.astype(int))
full = smf.logit("late ~ distance_km + C(day_part) + C(dow_name) + C(category) + C(payment_method)", d).fit(disp=0)
X = pd.get_dummies(o[["day_part", "dow_name", "category", "payment_method", "area"]].astype(str), drop_first=True).assign(distance=o.distance_km.values)
cv = StratifiedKFold(5, shuffle=True, random_state=1)
auc_late = roc_auc_score(o.is_late, cross_val_predict(LogisticRegression(max_iter=2000, C=0.05), X, o.is_late, cv=cv, method="predict_proba")[:, 1])
y_poor = o.poor_experience
auc_poor = roc_auc_score(y_poor, cross_val_predict(LogisticRegression(max_iter=2000, C=0.05), X, y_poor, cv=cv, method="predict_proba")[:, 1])
print({k: f"p={v[0]:.2f}, V={v[3]:.3f}" for k, v in tests.items()}, f"| area p={p_area:.2f}")
print(f"logit LR test p = {full.llr_pvalue:.2f} | pseudo R2 = {full.prsquared:.4f} | CV AUC late = {auc_late:.3f}, poor experience = {auc_poor:.3f}")
assert min(v[0] for v in tests.values()) > 0.05 and full.llr_pvalue > .05 and auc_late < .56
# %%
fig, axs = new_fig(h=6.6, nrows=2, ncols=3, left=0.15)
fig.subplots_adjust(wspace=.8, hspace=.28)
for ax, (name, tab) in zip(axs.flat, tabs.items()):
    yy = np.arange(len(tab))
    ax.errorbar(tab.rate * 100, yy, xerr=[(tab.rate - tab.lo) * 100, (tab.hi - tab.rate) * 100], fmt="o", color=GREEN, capsize=2.5, ms=5, lw=1.2)
    ax.axvline(late_rate * 100, color=GREY, ls="--", lw=1)
    ax.set_yticks(yy, [f"{i} ({n})" for i, n in zip(tab.index, tab.n)], fontsize=7.5); ax.invert_yaxis(); ax.set_xlim(15, 50); ax.set_xlabel("late rate, %", fontsize=8)
    clean_axes(ax, "x"); ax.set_title(f"{name}: {pfmt(tests[name][0])}", fontsize=9.5)
ax = axs.flat[5]
ar = area[area["size"] >= 3]
ax.scatter(ar["size"], ar["sum"] / ar["size"] * 100, s=9, alpha=.45, color=GREEN, linewidths=0)
nn = np.arange(3, ar["size"].max() + 1)
ax.plot(nn, (late_rate + 1.96 * np.sqrt(late_rate * (1 - late_rate) / nn)) * 100, color=GREY, lw=1, ls="--"); ax.plot(nn, (late_rate - 1.96 * np.sqrt(late_rate * (1 - late_rate) / nn)) * 100, color=GREY, lw=1, ls="--")
outside = ((ar["sum"] / ar["size"] > late_rate + 1.96 * np.sqrt(late_rate * (1 - late_rate) / ar["size"])) | (ar["sum"] / ar["size"] < late_rate - 1.96 * np.sqrt(late_rate * (1 - late_rate) / ar["size"]))).mean()
ax.set_xlabel("Orders in the area"); ax.set_ylim(-3, 103); clean_axes(ax, "y"); ax.set_title(f"Area ({len(area)}): {pfmt(p_area)}", fontsize=9.5); ax.set_ylabel("late rate, % (funnel plot)", fontsize=8)
note(ax, .97, .95, f"{outside:.0%} outside the 95% limits\n(5% expected by chance)", transform=ax.transAxes, ha="right", va="top", fontsize=8)
headline(fig, f"No driver explains lateness: it is about {late_rate:.0%} in every distance band, time of day, weekday, category, payment method and area",
         f"Late rate (95% Wilson CI), dashed line = overall {late_rate:.1%}. Logistic model on all drivers: likelihood-ratio {pfmt(full.llr_pvalue)}; cross-validated AUC {auc_late:.2f} (0.5 = coin flip)")
footnote(fig, "Source: data/clean fact_orders, dim_customer, dim_product. Late = delivery status not On Time. Distance, hour and area are unrelated to lateness, which points to an ETA that ignores them (to verify on real data).")
print(save(fig, "ds/rca_lateness_drivers"))
# %% [markdown]
# **Contribution view.** If one factor were the cause, some of its levels would carry many more late orders than the overall rate predicts. The waterfall shows that for the
# factor with the smallest p-value: each level's late orders minus the number expected at 30.6%; the levels net to zero by construction, whiskers show the 95% noise band.
# %%
best = min(tests, key=lambda k: tests[k][0])
tb = tabs[best].copy()
tb["excess"] = tb.late - tb.n * late_rate
tb["noise"] = 1.96 * np.sqrt(tb.n * late_rate * (1 - late_rate))
tb = tb.sort_values("excess", ascending=False)
print(best, "| largest gap", tb.excess.idxmax(), round(tb.excess.max(), 1), "orders, noise band +/-", round(tb.noise[tb.excess.idxmax()], 1), "| late orders", int(o.is_late.sum()))
fig, ax = new_fig(h=4.6, left=0.05)
import textwrap
waterfall(ax, [textwrap.fill(i, 11) + chr(10) + f"(n = {n})" for i, n in zip(tb.index, tb.n)], tb.excess.values, end_label="Net", fmt=lambda v: f"{v:+.0f}", total_fmt=lambda v: f"{v:+.0f}",
          err=[(v - h, v + h) for v, h in zip(tb.excess, tb.noise)])
ax.axhline(0, color=INK, lw=.8)
plt.setp(ax.get_xticklabels(), fontsize=7.5)
mx = tb.excess.idxmax()
n_out = int((tb.excess.abs() > tb.noise).sum())
headline(fig, f"By {best.lower()}, {n_out} of {len(tb)} levels sit outside their noise band (about {len(tb) * .05:.1f} expected by chance); the largest gap is {tb.excess.max():+.0f} late orders, {tb.excess.max() / o.is_late.sum():.1%} of all late orders",
         f"Late orders above (+) or below (-) the {late_rate:.1%} expectation, per {best.lower()} level ({best}: omnibus chi-square {pfmt(tests[best][0])}, the smallest of the five factors); whiskers = 95% noise band per level, not corrected for {len(tb)} comparisons")
footnote(fig, f"Source: data/clean fact_orders. Total late orders {int(o.is_late.sum()):,}. Levels net to zero by construction. A single level near its band is what comparing {len(tb)} levels produces; the omnibus test does not reject equal rates.")
print(save(fig, "ds/rca_lateness_contribution"))
# %% [markdown]
# **So what.** Lateness looks like a flat 30% tax on every slice, so a fix aimed at one slice (a zone, an hour, a category) has nothing to hit. In real data the first checks
# would be rider supply by hour and the ETA promise by distance; here both are flat, a sign that promised times are generated independently of the delivery.
#
# ## A2. Root cause of a poor experience: late only, low rating only, or both?
# **Method.** Split the 45.8% poor-experience orders into three exclusive groups, test whether lateness and low rating are independent (chi-square), then compare each group's share
# across factor levels (binomial test per cell; about 5% of 72 cells would flag by chance).
# %%
gx = o.experience.value_counts().reindex(["Good", "Late only", "Low rating only", "Both"])
rev = o.groupby("experience").order_total.sum().reindex(gx.index)
exp_both = o.is_late.mean() * o.low_rating.mean() * N
ct = pd.crosstab(o.is_late, o.low_rating); chi_ind, p_ind = stats.chi2_contingency(ct)[:2]
print(gx.to_dict(), "| both observed", int(gx["Both"]), "expected if independent", round(exp_both), "| independence p =", round(p_ind, 2))
assert round(rev[["Late only", "Low rating only", "Both"]].sum(), 2) == round(H["rar"], 2) == 5042193.50
FAC2 = {"Payment": "payment_method", "Distance": "dist_band", "Time of day": "day_part", "Category": "category"}
rows, flags, pmin = {}, {}, {}
for name, col in FAC2.items():
    t = pd.crosstab(o[col], o.experience); pmin[name] = stats.chi2_contingency(t)[1]
    for lev in t.index:
        r_ = {}
        for g in ["Late only", "Low rating only", "Both"]:
            base = (o.experience == g).mean(); k, n = t.loc[lev, g], t.loc[lev].sum()
            r_[g] = (k / n - base) * 100
            flags[(name, str(lev), g)] = stats.binomtest(int(k), int(n), base).pvalue < .05
        rows[(name, str(lev))] = r_
Dv = pd.DataFrame(rows).T
Fl = pd.Series(flags).unstack().reindex(Dv.index.map(lambda x: x), fill_value=False) if False else None
flag_df = pd.DataFrame({g: [flags[(a, b, g)] for a, b in Dv.index] for g in Dv.columns}, index=Dv.index)
print("flagged cells", int(flag_df.values.sum()), "of", flag_df.size, "| min chi-square p by factor", {k: round(v, 2) for k, v in pmin.items()})
# %%
fig, (a1, a2) = new_fig(h=6.4, ncols=2, gridspec_kw={"width_ratios": [1, 1.25]}, left=0.15)
share = gx / N
cols_ = [LTGREEN, YELLOW, "#E8B820", "#B98300"]
a1.barh(range(4), share.values, color=[GREEN, YELLOW, MIDGREEN, "#B98300"], height=.62)
for i, (g, v) in enumerate(share.items()):
    lo, hi = wilson(gx[g], N)
    a1.errorbar(v, i, xerr=[[v - lo], [hi - v]], fmt="none", ecolor=INK, capsize=3, elinewidth=1)
    a1.text(hi + .01, i, f"{v:.1%}" + chr(10) + f"{gx[g]:,} orders, {inr(rev[g])}", va="center", fontsize=8.5)
a1.set_yticks(range(4), ["Good", "Late only", "Low rating only", "Both late and 1-2 stars"]); a1.invert_yaxis(); a1.set_xlim(0, .95); a1.xaxis.set_visible(False)
a1.spines[["bottom", "left"]].set_visible(False); a1.tick_params(length=0)
a1.set_title(f"Share of orders. Both = {gx['Both']} vs {exp_both:.0f} expected if independent ({pfmt(p_ind)})", fontsize=9)
lab = [f"{a}: {b}" for a, b in Dv.index]
ann = Dv.map(lambda v: f"{v:+.1f}") + flag_df.map(lambda f: "*" if f else "")
sns.heatmap(Dv, ax=a2, cmap=DIV, center=0, vmin=-8, vmax=8, annot=ann, fmt="", annot_kws={"fontsize": 7}, linewidths=.5, linecolor="white", cbar_kws={"shrink": .6, "label": "points vs overall share"})
a2.set_yticklabels([l.replace("_", " ") for l in lab], rotation=0, fontsize=7.5); a2.set_ylabel(""); a2.set_xlabel(""); a2.tick_params(length=0); a2.xaxis.tick_top()
a2.set_title("Over / under-index vs overall share, points (* p < 0.05, one cell)", fontsize=9, pad=30)
headline(fig, f"Poor experience is two independent problems, not one: {share['Late only']:.0%} late only, {share['Low rating only']:.0%} low rating only, {share['Both']:.0%} both",
         f"45.8% of orders ({inr(H['rar'])}, the Revenue at Risk) are poor. Factor chi-square p {min(pmin.values()):.2f} to {max(pmin.values()):.2f}; {int(flag_df.values.sum())} of {flag_df.size} cells flag (about {flag_df.size * .05:.0f} by chance)")
footnote(fig, "Source: data/clean fact_orders. Low rating = 1-2 stars. 'Both' matches independence (lateness does not predict low ratings), so Revenue at Risk adds two separate exposures and fixing delivery alone leaves low ratings intact.")
print(save(fig, "ds/rca_poor_experience"))
# %% [markdown]
# **So what.** The two causes do not overlap more than chance, and neither concentrates in a slice. Late-only orders are the group a delivery fix can reach (about 1,000 orders); the
# low-rating-only group needs a different cause (product, service) that the feedback tags do not identify.
#
# ## A3. Revenue variance: volume, mix and AOV
# **Method.** Revenue = orders x AOV, with AOV split into category mix and within-category value:
# volume = (N1 - N0) x AOV0, mix = N1 x sum((share1 - share0) x AOV0 by category), AOV = N1 x sum(share1 x (AOV1 - AOV0) by category). The three effects add exactly to the revenue change.
# Uncertainty: mix and AOV effects by bootstrap (resampling orders within each period), volume by Poisson noise on the order counts.
# %%
def effects(a, b):
    N0, N1 = len(a), len(b); aov0 = a.order_total.mean()
    ca = a.groupby("category").order_total.agg(["size", "mean"]); cb = b.groupby("category").order_total.agg(["size", "mean"])
    cats = ca.index.union(cb.index)
    s0 = ca["size"].reindex(cats, fill_value=0) / N0; s1 = cb["size"].reindex(cats, fill_value=0) / N1
    a0 = ca["mean"].reindex(cats).fillna(aov0); a1 = cb["mean"].reindex(cats).fillna(0)
    vol = (N1 - N0) * aov0; mix = N1 * ((s1 - s0) * a0).sum(); rate = N1 * (s1 * (a1 - a0)).sum()
    return np.array([vol, mix, rate])
def bridge(a, b, nb=800):
    e = effects(a, b); tot = b.order_total.sum() - a.order_total.sum()
    assert abs(e.sum() - tot) < 1e-6, (e.sum(), tot)
    bs = []
    for _ in range(nb):
        bs.append(effects(a.sample(len(a), replace=True, random_state=int(rng.integers(1e9))), b.sample(len(b), replace=True, random_state=int(rng.integers(1e9)))))
    bs = np.array(bs); ci = np.percentile(bs, [2.5, 97.5], axis=0).T
    N0, N1 = len(a), len(b); half = 1.96 * np.sqrt(N0 + N1) * a.order_total.mean()
    ci[0] = [e[0] - half, e[0] + half]
    return e, ci, tot
mm = o[o.is_full_month]
def per(lo, hi=None):
    hi = hi or lo
    return mm[(mm.month_start >= lo) & (mm.month_start <= hi)]
MOM = [("Jul to Aug 2024", per("2024-07-01"), per("2024-08-01")), ("Aug to Sep 2024", per("2024-08-01"), per("2024-09-01")), ("Sep to Oct 2024", per("2024-09-01"), per("2024-10-01"))]
base23 = mm[(mm.month_start >= "2023-04-01") & (mm.month_start <= "2023-10-01")]; cur24 = mm[(mm.month_start >= "2024-04-01") & (mm.month_start <= "2024-10-01")]
res_mom = [(t, *bridge(a, b)) for t, a, b in MOM]
e_y, ci_y, tot_y = bridge(base23, cur24)
yoy = cur24.order_total.sum() / base23.order_total.sum() - 1
print("YoY Apr-Oct:", round(yoy, 4), "| change", round(tot_y), "| volume/mix/AOV", np.round(e_y).astype(int).tolist())
assert round(yoy, 4) == -0.0451
mo = (cur24.groupby("month_start").order_total.sum().values / base23.groupby("month_start").order_total.sum().values - 1)
assert [round(v * 100, 1) for v in mo] == [-2.8, -5.6, 6.7, 1.0, -12.4, -9.2, -7.0]
for t, e, ci_, tot in res_mom:
    print(t, round(tot), np.round(e).astype(int).tolist())
# %%
fig = blank_fig(h=7.4, left=0.07, pad=0.1)
gs = grid(fig, 2, 6, hspace=.5, wspace=1.2)
LB = ["Volume\n(orders)", "Mix\n(category)", "AOV\n(basket)"]
for i, (t, e, ci_, tot) in enumerate(res_mom):
    ax = fig.add_subplot(gs[0, 2 * i:2 * i + 2])
    waterfall(ax, LB, e / 1e5, end_label="Total\nchange", fmt=lambda v: f"{v:+.2f}", total_fmt=lambda v: f"{v:+.2f}", err=[(a_ / 1e5, b_ / 1e5) for a_, b_ in ci_])
    ax.axhline(0, color=INK, lw=.8); ax.set_title(f"{t}: {tot / 1e5:+.2f} L ({tot / per(MOM[i][1].month_start.iloc[0]).order_total.sum():+.1%})", fontsize=9.5)
ax = fig.add_subplot(gs[1, 0:3])
waterfall(ax, LB, e_y / 1e5, end_label="Total\nchange", fmt=lambda v: f"{v:+.2f}", total_fmt=lambda v: f"{v:+.2f}", err=[(a_ / 1e5, b_ / 1e5) for a_, b_ in ci_y])
ax.axhline(0, color=INK, lw=.8); ax.set_title(f"Apr to Oct 2024 vs 2023: {tot_y / 1e5:+.2f} L ({yoy:+.1%})", fontsize=9.5)
ax = fig.add_subplot(gs[1, 3:6])
mlab = [d.strftime("%b") for d in sorted(cur24.month_start.unique())]
ax.bar(range(7), mo * 100, color=[GOOD if v > 0 else BAD for v in mo], width=.6)
for i, v in enumerate(mo * 100): ax.text(i, v + (.6 if v > 0 else -.6), f"{v:+.1f}%", ha="center", va="bottom" if v > 0 else "top", fontsize=8.5)
ax.axhline(0, color=INK, lw=.8); ax.set_xticks(range(7), mlab); ax.set_ylim(-17, 11); ax.yaxis.set_visible(False); ax.spines[["left", "top", "right", "bottom"]].set_visible(False); ax.tick_params(length=0)
ax.set_title("Year on year by month: no consistent direction", fontsize=9.5)
headline(fig, f"Revenue changes are mostly noise: Apr to Oct 2024 is {yoy:+.1%} on 2023, split between fewer orders ({e_y[0] / 1e5:+.2f} L) and a lower AOV ({e_y[2] / 1e5:+.2f} L); neither interval excludes zero",
         "Revenue change in ₹ lakh split into volume (orders), mix (category) and AOV effects, with 95% intervals. Top: last three full month pairs. Bottom: year on year")
footnote(fig, "Source: data/clean fact_orders, full months only (Mar 2023 and Nov 2024 excluded). Bars start at zero change. Category is the mix dimension (order_total is unrelated to the item, so mix is expected to be about 0). YoY matches docs/reconciliation.md (-4.5%).")
print(save(fig, "ds/rca_revenue_bridge"))
# %% [markdown]
# **So what.** A 5% month-on-month move is what 250 orders a month produce by chance: the volume bar is the only one whose interval comes close to excluding zero, and only in the
# year-on-year view. Do not explain individual months; track a rolling 3-month total, and read the YoY decline (-4.5%) as weak evidence of fewer orders, not a mix or basket problem.
