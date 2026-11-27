# %% [markdown]
# # 04 · Data science: the key questions
# One chart per key question of `docs/data_science_review.md`: does lateness change the rating, does a poor experience cost the next order,
# does marketing spend buy revenue, do channels differ, do the stored segments mean anything. Each result carries its uncertainty;
# several answers are null, and a null with a wide interval is not proof of no effect.
# %%
import sys, warnings
from pathlib import Path
sys.path.insert(0, str(Path.cwd()))
warnings.filterwarnings("ignore")
from scipy import stats
import statsmodels.api as sm, statsmodels.formula.api as smf
from IPython.display import display
from viz_style import *
from data_io import *
o = orders_enriched(); mk = clean("fact_marketing")
END = o.order_date.max()
rng = np.random.default_rng(42)
# %% [markdown]
# ## Q1. Does a late delivery lower the rating?
# Method: mean rating by delivery status and by minutes late with 95% CIs; Welch difference late vs on time; Kruskal-Wallis and Spearman.
# %%
late, ont = o[o.is_late].rating, o[~o.is_late].rating
diff = late.mean() - ont.mean()
se = np.sqrt(late.var() / len(late) + ont.var() / len(ont))
ci = (diff - 1.96 * se, diff + 1.96 * se)
d_coh = diff / np.sqrt((late.var() + ont.var()) / 2)
p_kw = stats.kruskal(*[g.rating for _, g in o.groupby("delivery_status")]).pvalue
rho, p_rho = stats.spearmanr(o.rating, o.minutes_late)
print(f"late - on time = {diff:+.3f} stars (95% CI {ci[0]:+.3f} to {ci[1]:+.3f}), d = {d_coh:.2f}, Kruskal p = {p_kw:.2f}, Spearman {rho:+.3f} (p = {p_rho:.2f})")
assert abs(diff - 0.039) < .005 and abs(p_kw - .55) < .02
st = o.groupby("delivery_status").rating.agg(["mean", "sem", "size"]).reindex(["On Time", "Slightly Delayed", "Significantly Delayed"])
o["late_bin"] = pd.cut(o.minutes_late, [-6, 0, 5, 10, 15, 20, 25, 30], labels=["-5 to 0", "1 to 5", "6 to 10", "11 to 15", "16 to 20", "21 to 25", "26 to 30"])
lb = o.groupby("late_bin", observed=True).rating.agg(["mean", "sem", "size"])
fig, (a1, a2) = new_fig(h=4.6, ncols=2, gridspec_kw={"width_ratios": [1, 1.4]})
cols = [GREEN, YELLOW, "#B98300"]
a1.bar(range(3), st["mean"], color=cols, width=.6, yerr=1.96 * st["sem"], error_kw=dict(ecolor=INK, capsize=3, elinewidth=1))
for i, (mu, n) in enumerate(zip(st["mean"], st["size"])):
    a1.text(i, 0.15, f"{mu:.2f}\nn = {n:,}", ha="center", va="bottom", fontsize=9, color="white" if i != 1 else INK, fontweight="bold")
a1.set_xticks(range(3), ["On time", "Slightly\ndelayed", "Significantly\ndelayed"]); a1.set_ylim(0, 5); a1.set_ylabel("Mean rating (95% CI)"); clean_axes(a1)
a1.set_title("Rating by delivery status")
a2.errorbar(range(len(lb)), lb["mean"], yerr=1.96 * lb["sem"], fmt="o-", color=GREEN, capsize=3, lw=1.5)
a2.axhline(o.rating.mean(), color=GREY, ls="--", lw=1); a2.text(len(lb) - .6, o.rating.mean() + .03, f"all orders {o.rating.mean():.2f}", ha="right", va="bottom", fontsize=8.5, color=MUTED)
a2.set_xticks(range(len(lb)), lb.index); a2.set_ylim(1, 5); a2.set_xlabel("Minutes late vs promise"); a2.set_ylabel("Mean rating (95% CI)"); clean_axes(a2)
a2.set_title(f"Rating by minutes late: no slope (Spearman {rho:+.3f})")
headline(fig, f"Late orders are not rated lower: {diff:+.2f} stars (95% CI {ci[0]:+.2f} to {ci[1]:+.2f}), and rating does not fall as delay grows",
         f"Mean rating, 5,000 orders. Kruskal-Wallis by status {pfmt(p_kw)}; Cohen's d {d_coh:.2f}. Null result with a narrow interval: effects above about 0.11 stars are ruled out")
footnote(fig, "Source: data/clean fact_orders. Left axis starts at zero. The expected link (late -> low rating) is absent, so Revenue at Risk shows its two causes separately.")
print(save(fig, "ds/delay_vs_rating"))
# %% [markdown]
# ## Q2. Does a poor experience reduce the next order within 60 days?
# Method: orders with at least 60 days of follow-up (n = 4,507); logistic regression with customer-clustered standard errors; Wilson CIs on the rates.
# %%
s = o.sort_values(["customer_id", "order_date", "order_id"]).copy()
s["next_date"] = s.groupby("customer_id").order_date.shift(-1)
s["to_next"] = (s.next_date - s.order_date).dt.days
el = s[(END - s.order_date).dt.days >= 60].copy()
el["re60"] = (el.to_next <= 60).astype(int)
for c in ("poor_experience", "is_late", "low_rating"):
    el[c + "_i"] = el[c].astype(int)
def lor(v):
    f = smf.logit(f"re60 ~ {v}_i", el).fit(disp=0, cov_type="cluster", cov_kwds={"groups": el.customer_id})
    return np.exp(f.params.iloc[1]), np.exp(f.conf_int().iloc[1]).values, f.pvalues.iloc[1]
OR = {"Poor experience (late or 1-2 stars)": lor("poor_experience"), "Late alone": lor("is_late"), "Rating 1-2 alone": lor("low_rating")}
g = el.groupby("experience").re60.agg(["sum", "size"]).reindex(["Good", "Late only", "Low rating only", "Both"])
g["rate"] = g["sum"] / g["size"]; g["lo"], g["hi"] = wilson(g["sum"], g["size"])
good_rate = el[~el.poor_experience].re60.mean(); poor_rate = el[el.poor_experience].re60.mean()
print(f"n = {len(el):,} | reorder within 60 days: good {good_rate:.1%}, poor {poor_rate:.1%}")
print({k: (round(v[0], 2), np.round(v[1], 2).tolist(), round(v[2], 2)) for k, v in OR.items()})
assert len(el) == 4507 and round(good_rate, 3) == .184 and round(poor_rate, 3) == .169
orp = OR["Poor experience (late or 1-2 stars)"]
assert abs(orp[0] - .90) < .01 and abs(orp[2] - .19) < .02
fig, (a1, a2) = new_fig(h=4.6, ncols=2, gridspec_kw={"width_ratios": [1.2, 1]})
a1.bar(range(4), g.rate, color=[GREEN, YELLOW, YELLOW, "#B98300"], width=.6, yerr=[g.rate - g.lo, g.hi - g.rate], error_kw=dict(ecolor=INK, capsize=3, elinewidth=1))
for i, (r, n, h_) in enumerate(zip(g.rate, g["size"], g.hi)):
    a1.text(i, h_ + .006, f"{r:.1%}", ha="center", fontsize=9.5, fontweight="bold"); a1.text(i, .005, f"n = {n:,}", ha="center", fontsize=8, color="white" if i in (0, 3) else INK)
a1.set_xticks(range(4), ["Good", "Late only", "Rating 1-2\nonly", "Both"]); a1.set_ylim(0, .3); a1.yaxis.set_visible(False); a1.spines["left"].set_visible(False); a1.tick_params(length=0)
a1.set_title("Reordered within 60 days (95% Wilson CI)")
y_ = np.arange(3)[::-1]
for yy, (k, (v, c, p)) in zip(y_, OR.items()):
    a2.errorbar(v, yy, xerr=[[v - c[0]], [c[1] - v]], fmt="o", color=GREEN, capsize=4, ms=7)
    a2.text(1.62, yy, f"OR {v:.2f} ({c[0]:.2f} to {c[1]:.2f}), {pfmt(p)}", va="center", fontsize=8.5)
a2.axvline(1, color=INK, lw=1); a2.set_ylim(-.7, 2.7); a2.set_yticks(y_, list(OR)); a2.set_xlim(.6, 2.9); a2.set_xlabel("Odds ratio for reorder (1 = no effect)"); clean_axes(a2, "x")
a2.set_title("Effect on reorder odds, customer-clustered")
headline(fig, f"A poor experience may cut 60-day reorders ({poor_rate:.1%} vs {good_rate:.1%}) but the effect is not distinguishable from zero",
         f"{len(el):,} orders with 60+ days of follow-up. OR {orp[0]:.2f} (95% CI {orp[1][0]:.2f} to {orp[1][1]:.2f}): the data allow up to about a 23% cut in odds, or a small rise")
footnote(fig, "Source: data/clean fact_orders. Observational, not causal: experience is not randomised and customers are tracked only inside the data window. A null with this interval is not proof of no effect; see the win-back experiment sizing in the review.")
print(save(fig, "ds/reorder_after_poor_experience"))
# %% [markdown]
# ## Q3. Does more marketing spend bring more revenue?
# Method: log-log regression of attributed revenue on spend with HC3 errors and a 95% band; ROAS by spend quintile with bootstrap CIs.
# %%
lm = smf.ols("np.log(attributed_revenue) ~ np.log(spend)", mk).fit(cov_type="HC3")
el_, ci_el, p_el = lm.params.iloc[1], lm.conf_int().iloc[1].values, lm.pvalues.iloc[1]
rho_sr, p_sr = stats.spearmanr(mk.spend, mk.attributed_revenue)
mk["sq"] = pd.qcut(mk.spend, 5, labels=False)
def ratio_ci(d, n=1000):
    sp, rv = d.spend.values, d.attributed_revenue.values
    idx = rng.integers(0, len(d), (n, len(d)))
    r = rv[idx].sum(1) / sp[idx].sum(1)
    return rv.sum() / sp.sum(), np.percentile(r, 2.5), np.percentile(r, 97.5)
q = pd.DataFrame([ratio_ci(d) for _, d in mk.groupby("sq")], columns=["roas", "lo", "hi"])
print(f"elasticity {el_:.3f} (95% CI {ci_el[0]:.3f} to {ci_el[1]:.3f}), p = {p_el:.2f} | Spearman {rho_sr:+.3f} (p = {p_sr:.2f}) | ROAS by quintile {q.roas.round(2).tolist()}")
assert abs(el_ + .013) < .003 and [round(v, 2) for v in q.roas] == [4.26, 2.63, 1.97, 1.59, 1.27]
fig, (a1, a2) = new_fig(h=4.8, ncols=2, gridspec_kw={"width_ratios": [1.3, 1]})
a1.scatter(mk.spend / 1e3, mk.attributed_revenue / 1e3, s=6, alpha=.25, color=GREEN, linewidths=0)
xs = np.linspace(mk.spend.min(), mk.spend.max(), 60)
pr = lm.get_prediction(pd.DataFrame({"spend": xs})).summary_frame(alpha=.05)
a1.plot(xs / 1e3, np.exp(pr["mean"]) / 1e3, color=INK, lw=2, label=f"fitted: elasticity {el_:.2f}")
a1.fill_between(xs / 1e3, np.exp(pr["mean_ci_lower"]) / 1e3, np.exp(pr["mean_ci_upper"]) / 1e3, color=YELLOW, alpha=.7, lw=0)
a1.plot(xs / 1e3, mk.attributed_revenue.sum() / mk.spend.sum() * xs / 1e3, color=GREY, ls="--", lw=1.2, label="if revenue scaled with spend (ROAS 1.97)")
a1.set_xlabel("Spend per record, ₹ thousand"); a1.set_ylabel("Attributed revenue, ₹ thousand"); clean_axes(a1, "both"); a1.legend(loc="upper left")
a1.set_ylim(0, 10.5); a1.set_title("5,400 campaign records: revenue is flat in spend")
a2.bar(range(5), q.roas, color=GREEN, width=.6, yerr=[q.roas - q.lo, q.hi - q.roas], error_kw=dict(ecolor=INK, capsize=3, elinewidth=1))
for i, v in enumerate(q.roas): a2.text(i, q.hi[i] + .08, f"{v:.2f}", ha="center", fontsize=9.5, fontweight="bold")
a2.set_xticks(range(5), ["Q1\nlowest", "Q2", "Q3", "Q4", "Q5\nhighest"]); a2.set_xlabel("Spend quintile"); a2.set_ylim(0, 5); a2.yaxis.set_visible(False); a2.spines["left"].set_visible(False); a2.tick_params(length=0)
a2.set_title("ROAS by spend quintile (95% CI)")
headline(fig, f"Spending more does not bring more revenue: elasticity {el_:.2f} (95% CI {ci_el[0]:.2f} to {ci_el[1]:.2f}); ROAS 'falls' with spend only as a ratio effect",
         "Attributed revenue vs spend per campaign record (log-log fit with 95% band) and ROAS by spend quintile")
footnote(fig, "Source: data/clean fact_marketing. Attributed revenue is 2.9x order revenue, so it is not a response curve to trust. Recommendation: a holdout incrementality test, not a reallocation.")
print(save(fig, "ds/spend_revenue"))
# %% [markdown]
# ## Q4. Do channels or audiences differ in ROAS?
# Method: SUM/SUM ROAS with bootstrap 95% CIs by channel, audience and channel x audience; cells whose interval excludes the overall ROAS are flagged (about 1 of 16 expected by chance).
# %%
def boot_roas(d, n=1500):
    sp, rv = d.spend.values, d.attributed_revenue.values
    idx = rng.integers(0, len(d), (n, len(d)))
    r = rv[idx].sum(1) / sp[idx].sum(1)
    return rv.sum() / sp.sum(), *np.percentile(r, [2.5, 97.5])
overall = mk.attributed_revenue.sum() / mk.spend.sum()
ch = pd.DataFrame({k: boot_roas(d) for k, d in mk.groupby("channel")}, index=["roas", "lo", "hi"]).T
au = pd.DataFrame({k: boot_roas(d) for k, d in mk.groupby("target_audience")}, index=["roas", "lo", "hi"]).T
cells = {(a, b): boot_roas(d, 800) for (a, b), d in mk.groupby(["channel", "target_audience"])}
cell_roas = pd.Series({k: v[0] for k, v in cells.items()}).unstack()
flag = pd.Series({k: (v[1] > overall or v[2] < overall) for k, v in cells.items()}).unstack()
p_kw = stats.kruskal(*[g.roas for _, g in mk.groupby("channel")]).pvalue
print("overall", round(overall, 2), "| channels", ch.roas.round(2).to_dict(), "| flagged cells", int(flag.values.sum()), "of 16 | Kruskal(channel) p =", round(p_kw, 3))
assert round(overall, 2) == 1.97 and [round(v, 2) for v in ch.roas] == [1.92, 2.05, 1.99, 1.94]
fig, (a1, a2) = new_fig(h=4.8, ncols=2, gridspec_kw={"width_ratios": [1.1, 1]}, left=0.14)
allg = pd.concat([ch.sort_values("roas"), au.sort_values("roas")]); lab = list(allg.index)
yy = np.arange(len(allg)); yy = np.where(yy >= 4, yy + .8, yy)
a1.errorbar(allg.roas, yy, xerr=[allg.roas - allg.lo, allg.hi - allg.roas], fmt="o", color=GREEN, capsize=3)
for y_, (k, r) in zip(yy, allg.iterrows()): a1.text(2.28, y_, f"{r.roas:.2f}", va="center", fontsize=8.5)
a1.axvline(overall, color=GREY, ls="--", lw=1); a1.text(overall + .005, 8.35, f"overall {overall:.2f}", ha="left", fontsize=8.5, color=MUTED)
a1.set_yticks(yy, lab); a1.set_ylim(8.7, -1.1); a1.set_xlim(1.7, 2.35); a1.set_xlabel("ROAS (bootstrap 95% CI)"); clean_axes(a1, "x")
a1.text(1.71, -.75, "CHANNEL", fontsize=8, color=MUTED, fontweight="bold"); a1.text(1.71, 3.95, "AUDIENCE", fontsize=8, color=MUTED, fontweight="bold")
a1.set_title("Channels and audiences overlap almost completely")
ann = cell_roas.map(lambda v: f"{v:.2f}") + flag.map(lambda f: " *" if f else "")
sns.heatmap(cell_roas, ax=a2, cmap=SEQ_LIGHT, vmin=1.6, vmax=2.4, annot=ann, fmt="", annot_kws={"fontsize": 9}, linewidths=.8, linecolor="white", cbar_kws={"shrink": .75, "label": "ROAS"})
a2.set_xlabel(""); a2.set_ylabel(""); a2.tick_params(length=0); plt.setp(a2.get_yticklabels(), rotation=0); plt.setp(a2.get_xticklabels(), rotation=20)
a2.set_title(f"Channel x audience (* = CI excludes {overall:.2f}; {int(flag.values.sum())} of 16)")
headline(fig, f"Email leads at {ch.roas['Email']:.2f} and App trails at {ch.roas['App']:.2f}, a 7% gap that is too small and too uncertain to act on",
         f"ROAS = total attributed revenue / total spend; overall {overall:.2f}. Kruskal-Wallis on row ROAS by channel {pfmt(p_kw)}, by audience p = 0.53")
footnote(fig, "Source: data/clean fact_marketing. Sixteen cells compared at 95% means about 0.8 false flags by chance. Colour scale 1.6 to 2.4 is a narrow range chosen to expose small differences; the gaps are small.")
print(save(fig, "ds/roas_ci"))
# %% [markdown]
# ## Q5. Do the stored customer segments mean anything?
# Method: orders and revenue per ordering customer by the stored segment, mean with bootstrap CI, Kruskal-Wallis and eta-squared.
# %%
cs = o.groupby("customer_id").agg(n=("order_id", "size"), rev=("order_total", "sum"), seg=("segment", "first"))
p_n, p_r = (stats.kruskal(*[g[c] for _, g in cs.groupby("seg")]).pvalue for c in ("n", "rev"))
eta = smf.ols("rev ~ C(seg)", cs).fit().rsquared
print("customers", len(cs), "| Kruskal orders p", round(p_n, 2), "| revenue p", round(p_r, 2), "| eta2", round(eta, 4))
assert abs(p_n - .98) < .02 and abs(p_r - .61) < .02
order = ["New", "Regular", "Premium", "Inactive"]
fig, (a1, a2) = new_fig(h=4.4, ncols=2)
for ax, col, ttl, fm, p in [(a1, "n", "Orders per ordering customer", "{:.2f}", p_n), (a2, "rev", "Revenue per ordering customer, ₹", "{:,.0f}", p_r)]:
    mu = cs.groupby("seg")[col].mean().reindex(order)
    cis = np.array([boot_ci(cs[cs.seg == s_][col].values, n=1500) for s_ in order])
    ax.bar(range(4), mu, color=[GREEN, MIDGREEN, YELLOW, GREY], width=.6, yerr=[mu - cis[:, 0], cis[:, 1] - mu], error_kw=dict(ecolor=INK, capsize=3, elinewidth=1))
    for i, v in enumerate(mu): ax.text(i, cis[i, 1] * 1.02, fm.format(v), ha="center", fontsize=9.5, fontweight="bold")
    ax.set_xticks(range(4), [f"{s_}\n(n = {int((cs.seg == s_).sum())})" for s_ in order]); ax.set_ylim(0, cis[:, 1].max() * 1.18); ax.yaxis.set_visible(False)
    ax.spines["left"].set_visible(False); ax.tick_params(length=0); ax.set_title(f"{ttl}: {pfmt(p)}")
headline(fig, "The stored segments (New, Regular, Premium, Inactive) behave identically: 'Inactive' customers order as often as 'Premium' ones",
         f"Ordering customers by stored segment, mean with bootstrap 95% CI. Segment explains {eta:.2%} of revenue variance (eta-squared)")
footnote(fig, "Source: data/clean dim_customer and fact_orders (2,172 ordering customers). Null result: do not target on stored segment; behavioural RFM (notebook 05) is the replacement to test.")
print(save(fig, "ds/segment_value"))
