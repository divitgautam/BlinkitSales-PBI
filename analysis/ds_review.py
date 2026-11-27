"""Data-science review of the Blinkit dataset. Rerunnable and quiet: writes docs/ds/results.json and 5 PNGs.
Run: python analysis/ds_review.py   (needs pandas, numpy, scipy, statsmodels, matplotlib)
No personal fields are read (names, emails, phones, addresses are not in data/clean)."""
import json, warnings
from pathlib import Path
import numpy as np, pandas as pd
from scipy import stats
import statsmodels.api as sm, statsmodels.formula.api as smf
from statsmodels.miscmodels.ordinal_model import OrderedModel
from statsmodels.duration.hazard_regression import PHReg
from statsmodels.stats.power import NormalIndPower
from statsmodels.tsa.stattools import adfuller
from statsmodels.stats.diagnostic import acorr_ljungbox
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
warnings.filterwarnings("ignore")
ROOT = Path(__file__).resolve().parents[1]; CL = ROOT/"data/clean"; OUT = ROOT/"docs/ds"; OUT.mkdir(exist_ok=True, parents=True)
rng = np.random.default_rng(42); R = {}
o = pd.read_parquet(CL/"fact_orders.parquet"); cu = pd.read_parquet(CL/"dim_customer.parquet")
pr = pd.read_parquet(CL/"dim_product.parquet"); mk = pd.read_parquet(CL/"fact_marketing.parquet"); inv = pd.read_parquet(CL/"fact_inventory.parquet")
o = o.merge(cu[["customer_id", "area", "segment", "registration_date"]], on="customer_id", how="left").merge(pr[["product_id", "category", "price", "mrp"]], on="product_id", how="left", suffixes=("", "_p"))
o["dow"] = o.order_date.dt.dayofweek
o["disc"] = 1 - o.price/o.mrp
END = o.order_date.max()
BLUE, GREY, ORG = "#0C831F", "#8a8a8a", "#E4572E"


def sty(ax):
    ax.spines[["top", "right"]].set_visible(False)


def gini(x):
    x = np.sort(np.asarray(x, float)); n = len(x)
    return float((2*np.arange(1, n+1)-n-1).dot(x)/(n*x.sum()))


def boot(f, df, n=1000):
    idx = np.arange(len(df)); v = [f(df.iloc[rng.choice(idx, len(idx))]) for _ in range(n)]
    return [float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))]


def chi(a, b):
    t = pd.crosstab(a, b); c, p, d, _ = stats.chi2_contingency(t)
    return {"chi2": float(c), "p": float(p), "cramers_v": float(np.sqrt(c/(t.values.sum()*(min(t.shape)-1))))}


def kw(df, col, by):
    return float(stats.kruskal(*[g[col] for _, g in df.groupby(by)]).pvalue)


# ---------------- A customers
cs = o.groupby("customer_id").agg(n=("order_id", "size"), rev=("order_total", "sum"), first=("order_date", "min"), seg=("segment", "first"))
A = {}
A["customers"] = len(cs); A["repeat_share"] = float((cs.n >= 2).mean()); A["orders_per_cust_mean"] = float(cs.n.mean()); A["orders_per_cust_var"] = float(cs.n.var())
A["orders_dist"] = cs.n.value_counts().sort_index().to_dict()
sim = [np.bincount(rng.integers(0, len(cs), len(o)), minlength=len(cs)) for _ in range(200)]
A["random_assign_var"] = float(np.mean([s_.var() for s_ in sim])); A["random_assign_repeat_share"] = float(np.mean([(s_ >= 2).mean() for s_ in sim]))
A["segment_table"] = cs.groupby("seg").agg(customers=("n", "size"), orders_pc=("n", "mean"), rev_pc=("rev", "mean")).round(2).to_dict("index")
A["seg_kruskal_orders_p"] = kw(cs, "n", "seg"); A["seg_kruskal_rev_p"] = kw(cs, "rev", "seg")
A["seg_eta2_rev"] = float(smf.ols("rev~C(seg)", cs).fit().rsquared)
A["seg_aov_p"] = kw(o, "order_total", "segment"); A["aov_by_segment"] = o.groupby("segment").order_total.mean().round(1).to_dict()
A["repeat_share_of_rev"] = float(cs[cs.n >= 2].rev.sum()/cs.rev.sum())
o["cm"] = o.month_start.dt.to_period("M"); cs["cohort"] = cs["first"].dt.to_period("M")
oc = o.merge(cs[["cohort"]], left_on="customer_id", right_index=True); oc["k"] = [(a_-b_).n for a_, b_ in zip(oc.cm, oc.cohort)]
coh = oc.groupby(["cohort", "k"]).customer_id.nunique().unstack(fill_value=0); size = coh[0]
ret_m = coh.div(size, axis=0).astype(float); last_m = o.cm.max()
for c_ in ret_m.index:
    for k in ret_m.columns:
        if (c_ + int(k)) > last_m:
            ret_m.loc[c_, k] = np.nan
A["cohort_sizes_range"] = [int(size.min()), int(size.max())]
A["retention_by_k_mean"] = {int(k): round(float(ret_m[k].mean()), 3) for k in range(1, 7) if k in ret_m}
s = o.sort_values(["customer_id", "order_date", "order_id"]).copy(); s["gap"] = s.groupby("customer_id").order_date.diff().dt.days
A["gap_days_median"] = float(s.gap.median()); A["gap_days_mean"] = float(s.gap.mean()); A["gap_days_p90"] = float(s.gap.quantile(.9))
sec = s[s.groupby("customer_id").cumcount() == 1]; A["time_to_2nd_median"] = float(sec.gap.median()); A["time_to_2nd_n"] = int(len(sec))
rf = s.groupby("customer_id").agg(r=("order_date", lambda x: (END - x.max()).days), f=("order_id", "size"), m=("order_total", "sum"))
rf["R"] = pd.qcut(rf.r.rank(method="first"), 3, labels=[3, 2, 1]).astype(int); rf["F"] = pd.qcut(rf.f.rank(method="first"), 3, labels=[1, 2, 3]).astype(int)


def lab(r):
    if r.R == 3 and r.F == 3: return "Champions"
    if r.F == 3: return "Loyal, lapsing"
    if r.R == 3 and r.F == 1: return "Recent, light"
    if r.R == 1 and r.F == 1: return "Lost, light"
    return "Middle"


rf["seg"] = rf.apply(lab, axis=1); rt = rf.groupby("seg").agg(customers=("m", "size"), revenue=("m", "sum"), mean_orders=("f", "mean")); rt["rev_share"] = rt.revenue/rt.revenue.sum()
A["rfm"] = rt.round(3).to_dict("index")
cr = cs.rev.sort_values(ascending=False); cum = cr.cumsum()/cr.sum()
A["pareto_top10pct_share"] = float(cum.iloc[int(len(cr)*.1)-1]); A["pareto_top20pct_share"] = float(cum.iloc[int(len(cr)*.2)-1]); A["gini_revenue"] = gini(cs.rev)
A["gini_random_assign"] = float(np.mean([gini(sim[i]*o.order_total.mean()) for i in range(50)]))
A["orders_before_registration_share"] = float((o.order_date < o.registration_date).mean())
R["A"] = A

# ---------------- B basket / price
B = {}
B["discount_depth_mean"] = float(o.disc.mean()); B["discount_depth_range"] = [float(o.disc.min()), float(o.disc.max())]
B["spearman_disc_qty"] = [float(x) for x in stats.spearmanr(o.disc, o.quantity)]
B["spearman_price_qty"] = [float(x) for x in stats.spearmanr(o.unit_price, o.quantity)]
B["spearman_disc_ordertotal"] = [float(x) for x in stats.spearmanr(o.disc, o.order_total)]
B["corr_ordertotal_linevalue"] = float(o.order_total.corr(o.line_value)); B["corr_ordertotal_quantity"] = float(o.order_total.corr(o.quantity))
B["qty_dist"] = o.quantity.value_counts(normalize=True).sort_index().round(3).to_dict()
B["cat_by_segment"] = chi(o.category, o.segment); B["cat_by_area"] = chi(o.category, o.area); B["cat_by_payment"] = chi(o.category, o.payment_method)
B["n_areas"] = int(o.area.nunique())
hc = o.order_hour.value_counts().reindex(range(24), fill_value=0); B["hour_uniform_chi2_p"] = float(stats.chisquare(hc).pvalue); B["hour_max_min_ratio"] = float(hc.max()/hc.min()); B["hour_top3"] = hc.nlargest(3).to_dict()
dc = o.dow.value_counts().sort_index(); B["dow_uniform_chi2_p"] = float(stats.chisquare(dc).pvalue); B["dow_counts"] = dc.to_dict()
B["aov_by_hour_kruskal_p"] = kw(o, "order_total", "order_hour"); B["aov_by_dow_kruskal_p"] = kw(o, "order_total", "dow"); B["aov_by_category_kruskal_p"] = kw(o, "order_total", "category")
B["aov_by_payment"] = o.groupby("payment_method").order_total.mean().round(1).to_dict(); B["aov_by_payment_p"] = kw(o, "order_total", "payment_method")
B["order_total_cv"] = float(o.order_total.std()/o.order_total.mean()); B["order_total_range"] = [float(o.order_total.min()), float(o.order_total.max())]
B["margin_price_corr"] = float(pr.price.corr(pr.margin_percentage))
R["B"] = B

# ---------------- C delivery
Cc = {}
fml = "minutes_late ~ distance_km + C(order_hour) + C(dow) + C(area) + C(category)"
m = smf.ols(fml, o).fit(cov_type="HC3")
Cc["ols_r2"] = float(m.rsquared); Cc["ols_adj_r2"] = float(m.rsquared_adj); Cc["ols_f_p"] = float(m.f_pvalue)
Cc["distance_coef_per_km"] = float(m.params["distance_km"]); Cc["distance_ci"] = [float(x) for x in m.conf_int().loc["distance_km"]]; Cc["distance_p"] = float(m.pvalues["distance_km"])
Cc["sd_minutes_late"] = float(o.minutes_late.std()); Cc["distance_sd"] = float(o.distance_km.std()); Cc["std_effect_distance"] = float(m.params["distance_km"]*o.distance_km.std()/o.minutes_late.std())
an = sm.stats.anova_lm(smf.ols(fml, o).fit(), typ=2)
Cc["anova_p"] = {k: float(v) for k, v in an["PR(>F)"].items() if k != "Residual"}
Cc["anova_partial_eta2"] = {k: float(an.loc[k, "sum_sq"]/(an.loc[k, "sum_sq"]+an.loc["Residual", "sum_sq"])) for k in an.index if k != "Residual"}
Cc["spearman_dist_late"] = [float(x) for x in stats.spearmanr(o.distance_km, o.minutes_late)]
h_ = np.histogram(o.minutes_late, 10)[0]; Cc["minutes_late_hist_ratio"] = float(h_.max()/h_.min())
Cc["late_rate"] = float(o.is_late.mean()); Cc["late_rate_ci"] = [float(x) for x in sm.stats.proportion_confint(o.is_late.sum(), len(o), method="wilson")]
ao = o.groupby("area").is_late.agg(["mean", "size"]); Cc["late_by_area_range"] = [float(ao["mean"].min()), float(ao["mean"].max())]; Cc["areas"] = len(ao); Cc["late_by_area_n_min"] = int(ao["size"].min()); Cc["late_by_area_chi"] = chi(o.area, o.is_late)
Cc["late_by_hour_chi"] = chi(o.order_hour, o.is_late); Cc["late_by_dow_chi"] = chi(o.dow, o.is_late); Cc["late_by_cat_chi"] = chi(o.category, o.is_late)
lg = smf.logit("late ~ distance_km + C(dow) + C(category)", o.assign(late=o.is_late.astype(int))).fit(disp=0)
Cc["late_logit_or_per_km"] = float(np.exp(lg.params["distance_km"])); Cc["late_logit_or_ci"] = [float(x) for x in np.exp(lg.conf_int().loc["distance_km"])]; Cc["late_logit_p_km"] = float(lg.pvalues["distance_km"])
Cc["late_by_dist_tercile"] = o.groupby(pd.qcut(o.distance_km, 3)).is_late.mean().round(3).tolist()
raw = pd.read_csv(ROOT/"data/raw/blinkit_orders.csv", usecols=["store_id", "delivery_partner_id"])
Cc["store_ids_unique"] = int(raw.store_id.nunique()); Cc["partner_ids_unique"] = int(raw.delivery_partner_id.nunique()); Cc["orders_raw"] = len(raw)
R["C"] = Cc

# ---------------- D experience
D = {}
o["neg"] = (o.sentiment == "Negative").astype(int)
D["rating_dist"] = o.rating.value_counts(normalize=True).sort_index().round(3).to_dict(); D["rating_mean"] = float(o.rating.mean())
D["sentiment_dist"] = o.sentiment.value_counts(normalize=True).round(3).to_dict()
D["rating_by_status"] = o.groupby("delivery_status").rating.agg(["mean", "size"]).round(3).to_dict("index")
D["kruskal_rating_status_p"] = kw(o, "rating", "delivery_status")
D["spearman_rating_late"] = [float(x) for x in stats.spearmanr(o.rating, o.minutes_late)]
a, b = o[o.is_late].rating.to_numpy(), o[~o.is_late].rating.to_numpy()
D["rating_diff_late_vs_ontime"] = float(a.mean()-b.mean())
D["rating_diff_ci"] = [float(np.percentile([rng.choice(a, len(a)).mean()-rng.choice(b, len(b)).mean() for _ in range(2000)], q)) for q in (2.5, 97.5)]
D["cohens_d_late"] = float((a.mean()-b.mean())/np.sqrt((a.var()+b.var())/2))
X = pd.get_dummies(o[["payment_method", "segment", "category"]], drop_first=True).astype(float); X["minutes_late"] = o.minutes_late.astype(float); X["distance_km"] = o.distance_km
om = OrderedModel(o.rating, X, distr="logit").fit(method="bfgs", disp=0, maxiter=1000)
keep = [i for i in om.params.index if "/" not in str(i)]
pv = om.pvalues[keep]; cf = om.params[keep]
D["ordinal_min_p"] = float(pv.min()); D["ordinal_n_sig_005"] = int((pv < .05).sum()); D["ordinal_n_terms"] = int(len(pv))
D["ordinal_minutes_late_or_per_min"] = float(np.exp(cf["minutes_late"])); D["ordinal_minutes_late_ci"] = [float(x) for x in np.exp(om.conf_int().loc["minutes_late"])]; D["ordinal_minutes_late_p"] = float(pv["minutes_late"])
D["ordinal_sig_terms"] = {k: [round(float(np.exp(cf[k])), 3), round(float(pv[k]), 4)] for k in pv.index if pv[k] < .05}
D["rating_by_payment_p"] = kw(o, "rating", "payment_method"); D["rating_by_segment_p"] = kw(o, "rating", "segment"); D["rating_by_category_p"] = kw(o, "rating", "category"); D["rating_by_fbcat_p"] = kw(o, "rating", "feedback_category")
lgn = smf.logit("neg ~ minutes_late + C(payment_method)", o).fit(disp=0); D["neg_or_per_min_late"] = float(np.exp(lgn.params["minutes_late"])); D["neg_p_late"] = float(lgn.pvalues["minutes_late"])
D["sentiment_vs_rating"] = chi(o.sentiment, o.rating); D["sentiment_by_rating"] = pd.crosstab(o.rating, o.sentiment, normalize="index").round(2).to_dict("index")
D["fbcat_share"] = o.feedback_category.value_counts(normalize=True).round(3).to_dict(); D["fbcat_vs_status"] = chi(o.feedback_category, o.delivery_status)
D["late_rate_when_fbcat_delivery"] = float(o[o.feedback_category == "Delivery"].is_late.mean()); D["late_rate_other_fbcat"] = float(o[o.feedback_category != "Delivery"].is_late.mean())
D["fbcat_vs_sentiment"] = chi(o.feedback_category, o.sentiment)
s = s.merge(o[["order_id", "poor_experience", "rating"]], on="order_id", suffixes=("", "_o"))
s["next_date"] = s.groupby("customer_id").order_date.shift(-1); s["to_next"] = (s.next_date-s.order_date).dt.days
el = s[(END-s.order_date).dt.days >= 60].copy(); el["re30"] = (el.to_next <= 30).astype(int); el["re60"] = (el.to_next <= 60).astype(int)
el["poor"] = el.poor_experience.astype(int); el["late"] = el.is_late.astype(int); el["low"] = (el.rating <= 2).astype(int)
D["next_n"] = int(len(el)); D["reorder30_base"] = float(el.re30.mean()); D["reorder60_base"] = float(el.re60.mean())
for v in ["poor", "late", "low"]:
    f = smf.logit(f"re60 ~ {v}", el).fit(disp=0, cov_type="cluster", cov_kwds={"groups": el.customer_id})
    D[f"reorder60_{v}"] = {"OR": float(np.exp(f.params[v])), "p": float(f.pvalues[v]), "CI": [float(x) for x in np.exp(f.conf_int().loc[v])], "rates": el.groupby(v).re60.mean().round(4).to_dict()}
cx = s.copy(); cx["event"] = cx.next_date.notna().astype(int); cx["t"] = np.where(cx.event == 1, cx.to_next, (END-cx.order_date).dt.days).astype(float); cx = cx[cx.t > 0].copy()
cx["late"] = cx.is_late.astype(float); cx["low"] = (cx.rating <= 2).astype(float); cx["poor"] = cx.poor_experience.astype(float)
for lab_, d_ in [("all_orders", cx), ("first_order_only", cx[cx.groupby("customer_id").cumcount() == 0])]:
    r = PHReg(d_.t.to_numpy(), d_[["poor"]].to_numpy(), status=d_.event.to_numpy()).fit(disp=0)
    D[f"cox_poor_{lab_}"] = {"HR": float(np.exp(r.params[0])), "CI": [float(x) for x in np.exp(r.conf_int()[0])], "p": float(r.pvalues[0]), "n": int(len(d_))}
r = PHReg(cx.t.to_numpy(), cx[["late", "low"]].to_numpy(), status=cx.event.to_numpy()).fit(disp=0)
D["cox_late_low"] = {"HR": [float(x) for x in np.exp(r.params)], "p": [float(x) for x in r.pvalues]}
R["D"] = D

# ---------------- E marketing
E = {}
mk["ctr"] = mk.clicks/mk.impressions; mk["cvr"] = mk.conversions/mk.clicks
ratio = lambda x: x.attributed_revenue.sum()/x.spend.sum()
E["rows"] = len(mk); E["roas_row_mean"] = float(mk.roas.mean()); E["roas_row_sd"] = float(mk.roas.std()); E["roas_row_pcts"] = [float(x) for x in mk.roas.quantile([.05, .25, .5, .75, .95])]
E["share_rows_roas_lt1"] = float((mk.roas < 1).mean()); E["roas_overall"] = float(ratio(mk)); E["roas_overall_ci"] = boot(ratio, mk)
hh = np.histogram(mk.roas, 10)[0]; E["roas_hist_ratio"] = float(hh.max()/hh.min())
for nm, col in [("channel", "channel"), ("audience", "target_audience")]:
    E[nm] = {k: {"roas": float(ratio(d)), "ci": boot(ratio, d)} for k, d in mk.groupby(col)}
    E[nm+"_kruskal_p"] = kw(mk, "roas", col)
cells = {f"{a_} x {b_}": {"roas": float(ratio(d)), "n": len(d), "ci": boot(ratio, d, 500)} for (a_, b_), d in mk.groupby(["channel", "target_audience"])}
E["cells_n"] = len(cells); E["cells_ci_excl_overall"] = [k for k, v in cells.items() if v["ci"][0] > E["roas_overall"] or v["ci"][1] < E["roas_overall"]]
E["cell_roas_range"] = [min(v["roas"] for v in cells.values()), max(v["roas"] for v in cells.values())]
tw = sm.stats.anova_lm(smf.ols("roas ~ C(channel)*C(target_audience)", mk).fit(), typ=2); E["twoway_anova_p"] = {k: float(v) for k, v in tw["PR(>F)"].items() if k != "Residual"}
lm = smf.ols("np.log(attributed_revenue) ~ np.log(spend)", mk).fit(cov_type="HC3"); E["elasticity"] = float(lm.params.iloc[1]); E["elasticity_ci"] = [float(x) for x in lm.conf_int().iloc[1]]; E["elasticity_r2"] = float(lm.rsquared)
E["spearman_spend_rev"] = [float(x) for x in stats.spearmanr(mk.spend, mk.attributed_revenue)]
mk["sq"] = pd.qcut(mk.spend, 5, labels=False); E["roas_by_spend_quintile"] = [round(float(ratio(d)), 3) for _, d in mk.groupby("sq")]
E["spearman_spend_roas"] = [float(x) for x in stats.spearmanr(mk.spend, mk.roas)]
E["ctr"] = float(mk.clicks.sum()/mk.impressions.sum()); E["cvr"] = float(mk.conversions.sum()/mk.clicks.sum()); E["cpa"] = float(mk.spend.sum()/mk.conversions.sum())
E["spearman_ctr_cvr"] = [float(x) for x in stats.spearmanr(mk.ctr, mk.cvr)]; E["spearman_cvr_roas"] = [float(x) for x in stats.spearmanr(mk.cvr, mk.roas)]; E["spearman_conv_rev"] = [float(x) for x in stats.spearmanr(mk.conversions, mk.attributed_revenue)]
E["rev_per_conversion"] = float(mk.attributed_revenue.sum()/mk.conversions.sum()); E["attr_rev_vs_orders_rev"] = float(mk.attributed_revenue.sum()/o.order_total.sum()); E["total_spend"] = float(mk.spend.sum())
E["conversions_per_order"] = float(mk.conversions.sum()/len(o))
R["E"] = E

# ---------------- F inventory
F = {}
iv = inv.merge(pr[["product_id", "category"]], on="product_id"); F["damage_rate"] = float(iv.damaged_stock.sum()/iv.stock_received.sum())
g = iv.groupby("category")[["damaged_stock", "stock_received"]].sum(); g["rate"] = g.damaged_stock/g.stock_received
F["damage_by_category"] = g.rate.round(4).to_dict(); F["damage_cat_range"] = [float(g.rate.min()), float(g.rate.max())]
F["damage_cat_chi2_p"] = float(stats.chi2_contingency(np.c_[g.damaged_stock, g.stock_received-g.damaged_stock])[1])
gp = iv.groupby("product_id")[["damaged_stock", "stock_received"]].sum(); gp["rate"] = gp.damaged_stock/gp.stock_received
F["damage_product_range"] = [float(gp.rate.min()), float(gp.rate.max())]; F["damage_product_sd"] = float(gp.rate.std())
F["damage_product_sd_expected_binomial"] = float(np.sqrt(F["damage_rate"]*(1-F["damage_rate"])/gp.stock_received).mean())
sh = pr[["product_id", "shelf_life_days"]].merge(gp.reset_index()[["product_id", "rate"]]); F["spearman_shelf_damage"] = [float(x) for x in stats.spearmanr(sh.shelf_life_days, sh.rate)]
ud = o.groupby(["product_id", "month_start"]).quantity.sum().rename("units").reset_index(); vm = inv.merge(ud, on=["product_id", "month_start"], how="left"); vm["units"] = vm.units.fillna(0)
F["stock_received_total"] = int(inv.stock_received.sum()); F["units_sold_total"] = int(o.quantity.sum()); F["received_to_sold_ratio"] = float(inv.stock_received.sum()/o.quantity.sum())
F["spearman_received_sold_pm"] = [float(x) for x in stats.spearmanr(vm.stock_received, vm.units)]
pp = vm.groupby("product_id")[["stock_received", "units"]].sum(); F["spearman_received_sold_product"] = [float(x) for x in stats.spearmanr(pp.stock_received, pp.units)]
pp["ratio"] = pp.stock_received/pp.units.replace(0, np.nan); F["ratio_product_median"] = float(pp.ratio.median()); F["ratio_product_p10_p90"] = [float(x) for x in pp.ratio.quantile([.1, .9])]; F["products_zero_sales"] = int((pp.units == 0).sum()); F["products"] = len(pp)
F["damaged_value_at_list_price"] = float(inv.merge(pr[["product_id", "price"]], on="product_id").eval("damaged_stock*price").sum())
R["F"] = F

# ---------------- G forecasting
G = {}
mm = o[o.is_full_month].groupby("month_start").order_total.sum(); G["n_months"] = len(mm); t = np.arange(len(mm))
sl = sm.OLS(mm.values, sm.add_constant(t)).fit(); G["trend_slope_per_month"] = float(sl.params[1]); G["trend_ci"] = [float(x) for x in sl.conf_int()[1]]; G["trend_p"] = float(sl.pvalues[1]); G["trend_r2"] = float(sl.rsquared)
G["mean_month"] = float(mm.mean()); G["monthly_cv"] = float(mm.std()/mm.mean())
kt = stats.kendalltau(t, mm.values); G["kendall_tau_p"] = [float(kt.statistic), float(kt.pvalue)]
G["adf_p"] = float(adfuller(mm.values, maxlag=2)[1]); G["ljung_box_p_lag6"] = float(acorr_ljungbox(mm.values-mm.mean(), lags=[6]).lb_pvalue.iloc[0])
byc = mm.groupby(mm.index.month); yo = byc.apply(lambda x: x.iloc[-1]/x.iloc[0]-1 if len(x) == 2 else np.nan).dropna()
G["yoy_mean_change_pct"] = float(yo.mean()); G["yoy_t_p"] = float(stats.ttest_1samp(yo, 0).pvalue); G["yoy_n"] = int(len(yo))
G["seasonal_corr_lag12"] = float(np.corrcoef(mm.values[12:], mm.values[:-12])[0, 1])
dd = o.groupby("order_date").order_total.sum(); dd = dd.reindex(pd.date_range(dd.index.min(), dd.index.max()), fill_value=0)
G["daily_dow_kruskal_p"] = float(stats.kruskal(*[dd[dd.index.dayofweek == k] for k in range(7)]).pvalue)
sd = float(mm.diff().dropna().std()); G["naive_step_sd"] = sd; G["naive_pi95_halfwidth"] = float(1.96*sd); G["naive_pi95_pct_of_mean"] = float(1.96*sd/mm.mean())
G["mean_model_pi95_halfwidth"] = float(1.96*mm.std()*np.sqrt(1+1/len(mm))); G["mean_model_pi95_pct"] = G["mean_model_pi95_halfwidth"]/G["mean_month"]
cov = [abs(mm.iloc[i]-mm.iloc[:i].mean()) <= 1.96*mm.iloc[:i].std()*np.sqrt(1+1/i) for i in range(8, len(mm))]
G["mean_model_pi95_coverage"] = float(np.mean(cov)); G["coverage_n"] = len(cov)
nm_err = [abs(mm.iloc[i+1]-mm.iloc[i])/mm.iloc[i+1] for i in range(9, len(mm)-1)]; mn_err = [abs(mm.iloc[i+1]-mm.iloc[:i+1].mean())/mm.iloc[i+1] for i in range(9, len(mm)-1)]
G["backtest_mape_naive"] = float(np.mean(nm_err)); G["backtest_mape_expanding_mean"] = float(np.mean(mn_err))
R["G"] = G

# ---------------- sizing and experiments (observed variance)
S = {}
aov, sdv = float(o.order_total.mean()), float(o.order_total.std()); S["aov"] = aov; S["aov_sd"] = sdv


def n_prop(p0, d):
    h = 2*np.arcsin(np.sqrt(p0+d))-2*np.arcsin(np.sqrt(p0)); return int(np.ceil(NormalIndPower().solve_power(effect_size=abs(h), alpha=.05, power=.8, ratio=1)))


def n_mean(sd_, d):
    return int(np.ceil(2*((stats.norm.ppf(.975)+stats.norm.ppf(.8))*sd_/d)**2))


p0 = D["reorder60_base"]; S["reorder60_p0"] = p0
for d_ in (.02, .03, .05): S[f"n_arm_reorder60_plus{int(d_*100)}pt"] = n_prop(p0, d_)
S["n_arm_aov_5pct"] = n_mean(sdv, .05*aov); S["n_arm_aov_10pct"] = n_mean(sdv, .10*aov)
S["rating_sd"] = float(o.rating.std()); S["n_arm_rating_0.1"] = n_mean(S["rating_sd"], .1)
S["late_p0"] = float(o.is_late.mean()); S["n_arm_late_minus3pt"] = n_prop(S["late_p0"]-.03, .03); S["n_arm_late_minus5pt"] = n_prop(S["late_p0"]-.05, .05)
S["minutes_late_sd"] = float(o.minutes_late.std()); S["n_arm_minutes_late_1min"] = n_mean(S["minutes_late_sd"], 1.0)
S["roas_row_sd"] = E["roas_row_sd"]; S["n_rows_arm_roas_0.1"] = n_mean(E["roas_row_sd"], .1); S["n_rows_arm_roas_0.2"] = n_mean(E["roas_row_sd"], .2)
days = (o.order_date.max()-o.order_date.min()).days+1; S["orders_per_day"] = float(len(o)/days); S["customers_active"] = len(cs)
S["revenue_last12_full"] = float(o[(o.month_start >= "2023-11-01") & (o.month_start <= "2024-10-01")].order_total.sum())
S["share_orders_repeat_cust"] = float((o.customer_id.map(cs.n) >= 2).mean())
R["S"] = S
json.dump(R, open(OUT/"results.json", "w"), indent=1, default=lambda x: x.item() if hasattr(x, "item") else str(x))

# ---------------- charts (5)
fig, ax = plt.subplots(figsize=(6, 3.4)); p = ret_m.iloc[:, 1:7]; im = ax.imshow(p.values.astype(float), cmap="Greens", vmin=0, aspect="auto")
ax.set_xticks(range(p.shape[1])); ax.set_xticklabels([f"M+{k}" for k in p.columns]); ax.set_yticks(range(len(p))); ax.set_yticklabels([str(x) for x in p.index], fontsize=6)
ax.set_title("Cohort retention by first-order month", fontsize=9, loc="left"); plt.colorbar(im, ax=ax, shrink=.8); fig.tight_layout(); fig.savefig(OUT/"cohort_retention.png", dpi=110); plt.close(fig)
fig, ax = plt.subplots(figsize=(5, 3.4)); x = np.arange(1, len(cum)+1)/len(cum); ax.plot(x, cum.values, color=BLUE, label="actual"); ax.plot([0, 1], [0, 1], color=GREY, ls="--", lw=1)
rs = np.sort(np.bincount(rng.integers(0, len(cs), len(o)), minlength=len(cs)))[::-1]; ax.plot(x, np.cumsum(rs)/rs.sum(), color=ORG, lw=1, label="orders assigned at random")
ax.legend(frameon=False, fontsize=8); ax.set_title("Customer revenue concentration vs random assignment", fontsize=9, loc="left"); ax.set_xlabel("share of customers"); ax.set_ylabel("cumulative revenue share"); sty(ax); fig.tight_layout(); fig.savefig(OUT/"pareto.png", dpi=110); plt.close(fig)
fig, ax = plt.subplots(figsize=(5.4, 3)); names = list(E["channel"])+list(E["audience"]); vals = [E["channel"][k] for k in E["channel"]]+[E["audience"][k] for k in E["audience"]]
for i, v in enumerate(vals): ax.errorbar(v["roas"], i, xerr=[[v["roas"]-v["ci"][0]], [v["ci"][1]-v["roas"]]], fmt="o", color=BLUE, capsize=3)
ax.axvline(E["roas_overall"], color=GREY, ls="--", lw=1); ax.set_yticks(range(len(names))); ax.set_yticklabels(names, fontsize=8); ax.invert_yaxis(); ax.set_xlabel("ROAS (95% bootstrap CI)"); ax.set_title("ROAS by channel and audience", fontsize=9, loc="left"); sty(ax); fig.tight_layout(); fig.savefig(OUT/"roas_ci.png", dpi=110); plt.close(fig)
fig, ax = plt.subplots(figsize=(5, 3.4)); ax.scatter(mk.spend, mk.attributed_revenue, s=4, alpha=.3, color=BLUE); xs = np.linspace(mk.spend.min(), mk.spend.max(), 50)
ax.plot(xs, np.exp(lm.params.iloc[0])*xs**lm.params.iloc[1], color=ORG, label="log-log fit"); ax.plot(xs, E["roas_overall"]*xs, color=GREY, ls="--", lw=1, label="constant ROAS"); ax.legend(frameon=False, fontsize=8)
ax.set_xlabel("spend"); ax.set_ylabel("attributed revenue"); ax.set_title(f"Spend vs revenue, elasticity {E['elasticity']:.2f}", fontsize=9, loc="left"); sty(ax); fig.tight_layout(); fig.savefig(OUT/"spend_revenue.png", dpi=110); plt.close(fig)
fig, ax = plt.subplots(figsize=(6, 3)); ax.plot(mm.index, mm.values/1e5, marker="o", color=BLUE, ms=3); hw = G["mean_model_pi95_halfwidth"]/1e5
ax.axhline(mm.mean()/1e5, color=GREY, ls="--"); ax.fill_between(mm.index, mm.mean()/1e5-hw, mm.mean()/1e5+hw, color=GREY, alpha=.15)
ax.set_ylabel("revenue, lakh"); ax.set_title("Monthly revenue with 95% prediction band of the mean model", fontsize=9, loc="left"); sty(ax); fig.tight_layout(); fig.savefig(OUT/"monthly_revenue.png", dpi=110); plt.close(fig)
